import json
import os
import numpy as np
import torch
from collections import OrderedDict
from copy import deepcopy

from r2d2.controllers.oculus_controller import VRPolicy
from r2d2.evaluation.policy_wrapper import PolicyWrapperRobomimic
from r2d2.robot_env import RobotEnv
from r2d2.user_interface.data_collector import DataCollecter
from r2d2.user_interface.gui import RobotGUI

import robomimic.utils.file_utils as FileUtils
import robomimic.utils.torch_utils as TorchUtils
import robomimic.utils.tensor_utils as TensorUtils

def eval_launcher(variant, run_id, exp_id):
    # Get Directory #
    dir_path = os.path.dirname(os.path.realpath(__file__))

    # Prepare Log Directory #
    variant["exp_name"] = os.path.join(variant["exp_name"], "run{0}/id{1}/".format(run_id, exp_id))
    log_dir = os.path.join(dir_path, "../../evaluation_logs", variant["exp_name"])

    # Set Random Seeds #
    torch.manual_seed(variant["seed"])
    np.random.seed(variant["seed"])

    # Set Compute Mode #
    use_gpu = variant.get("use_gpu", False)
    torch.device("cuda:0" if use_gpu else "cpu")

    ckpt_path = variant["ckpt_path"]
    task = variant["task"]
    layout_id = variant["layout_id"]

    device = TorchUtils.get_torch_device(try_to_use_cuda=True)
    ckpt_dict = FileUtils.maybe_dict_from_checkpoint(ckpt_path=ckpt_path)
    config = json.loads(ckpt_dict["config"])

    ### infer image size ###
    imsize = ckpt_dict["shape_metadata"]["all_shapes"]["camera/image/hand_camera_image"][2]

    ckpt_dict["config"] = json.dumps(config)
    policy, _ = FileUtils.policy_from_checkpoint(ckpt_dict=ckpt_dict, device=device, verbose=True)

    # determine the action space (relative or absolute)
    action_keys = config.train.action_keys
    if "action/rel_pos" in action_keys:
        action_space = "cartesian_velocity"
        for k in action_keys:
            assert not k.startswith("action/abs_")
    elif "action/abs_pos" in action_keys:
        action_space = "cartesian_position"
        for k in action_keys:
            assert not k.startswith("action/rel_")
    else:
        raise ValueError

    # Prepare Policy Wrapper #
    data_processing_kwargs = dict(
        timestep_filtering_kwargs=dict(
            action_space=action_space,
            robot_state_keys=["cartesian_position", "gripper_position", "joint_positions"],
            camera_extrinsics=[],
        ),
        image_transform_kwargs=dict(
            remove_alpha=True,
            bgr_to_rgb=True,
            to_tensor=True,
            augment=False,
        ),
    )
    timestep_filtering_kwargs = data_processing_kwargs.get("timestep_filtering_kwargs", {})
    image_transform_kwargs = data_processing_kwargs.get("image_transform_kwargs", {})

    policy_data_processing_kwargs = {}
    policy_timestep_filtering_kwargs = policy_data_processing_kwargs.get("timestep_filtering_kwargs", {})
    policy_image_transform_kwargs = policy_data_processing_kwargs.get("image_transform_kwargs", {})

    policy_timestep_filtering_kwargs.update(timestep_filtering_kwargs)
    policy_image_transform_kwargs.update(image_transform_kwargs)

    wrapped_policy = PolicyWrapperRobomimic(
        policy=policy,
        timestep_filtering_kwargs=policy_timestep_filtering_kwargs,
        image_transform_kwargs=policy_image_transform_kwargs,
        frame_stack=config.train.frame_stack,
        eval_mode=True,
    )

    # Prepare Environment #
    policy_action_space = policy_timestep_filtering_kwargs["action_space"]

    camera_kwargs = dict(
        hand_camera=dict(image=True, concatenate_images=False, resolution=(imsize, imsize), resize_func="cv2"),
        varied_camera=dict(image=True, concatenate_images=False, resolution=(imsize, imsize), resize_func="cv2"),
    )
    
    policy_camera_kwargs = {}
    policy_camera_kwargs.update(camera_kwargs)

    env = RobotEnv(action_space=policy_action_space, camera_kwargs=policy_camera_kwargs)
    controller = VRPolicy()

    # Launch GUI #
    data_collector = DataCollecter(
        env=env,
        controller=controller,
        policy=wrapped_policy,
        save_traj_dir=log_dir,
        save_data=variant.get("save_data", True),
    )
    RobotGUI(robot=data_collector)