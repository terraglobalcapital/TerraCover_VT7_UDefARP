# coding=utf-8
# ------------------------------------------------------------------------
#
#   Copyright:          © Terra Global Capital. All rights reserved.
#   Author:             david.montoya@terraglobalcapital.com
#   Python version:     3.11
#   GDAL version:       3.10.3
#   Year:               2025
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------

"""
VT7 Folder Structure Management

This module contains the VT7FolderStructure class for managing the folder structure
of VT7 Benchmark Model workflow outputs.
"""

import os


class VT7FolderStructure:
    '''
    VT7 Benchmark Model folder structure manager

    Creates and manages the folder structure for VT7 Benchmark Model workflow:
    - 1_Testing Stage
        - Models created with create_testing_models()
    - 2_Application Stage
        - Models created with create_application_models()

    Usage:
        # Create base structure
        folders = VT7FolderStructure(base_folder)

        # Create testing stage models
        folders.create_testing_models(bcm_testing=True, alt_testing=False)

        # Create application stage models
        folders.create_application_models(bcm_application=True, alt_application=True)
    '''

    def __init__(self, base_folder):
        '''
        Initialize VT7 folder structure with base folders only.

        :param base_folder: base folder where the structure will be created
        '''
        self.base_folder = base_folder

        # Define base folder paths
        self.testing_stage = os.path.join(base_folder, '1_Testing Stage')
        self.application_stage = os.path.join(base_folder, '2_Application Stage')

        # Testing stage model attributes (initialized with paths)
        self.testing_benchmark_model = os.path.join(self.testing_stage, '1_Benchmark Model')
        self.testing_benchmark_fitting = os.path.join(self.testing_benchmark_model, '1_Fitting Phase (CAL)')
        self.testing_benchmark_prediction = os.path.join(self.testing_benchmark_model, '2_Prediction Phase (CNF)')
        self.testing_benchmark_evaluation = os.path.join(self.testing_benchmark_model, '3_Model Evaluation')
        self.testing_alternative_model = os.path.join(self.testing_stage, '2_Alternative Model')
        self.testing_alternative_fitting = os.path.join(self.testing_alternative_model, '1_Fitting Phase (CAL)')
        self.testing_alternative_prediction = os.path.join(self.testing_alternative_model, '2_Prediction Phase (CNF)')
        self.testing_alternative_evaluation = os.path.join(self.testing_alternative_model, '3_Model Evaluation')

        # Application stage model attributes (initialized with paths)
        self.application_benchmark_model = os.path.join(self.application_stage, '1_Benchmark Model')
        self.application_benchmark_fitting = os.path.join(self.application_benchmark_model, '1_Fitting Phase (HRP)')
        self.application_benchmark_prediction = os.path.join(self.application_benchmark_model, '2_Prediction Phase (VP)')
        self.application_alternative_model = os.path.join(self.application_stage, '2_Alternative Model')
        self.application_alternative_fitting = os.path.join(self.application_alternative_model, '1_Fitting Phase (HRP)')
        self.application_alternative_prediction = os.path.join(self.application_alternative_model, '2_Prediction Phase (VP)')

        # Create initial folders
        self._create_base_folders()

    def _create_base_folders(self):
        '''Create base folder structure (Testing Stage only; Application Stage is created on demand)'''
        os.makedirs(self.testing_stage, exist_ok=True)

    def create_testing_models(self, bcm_testing=False, alt_testing=False,
                               bcm_cal=False, bcm_cnf=False, bcm_eval=False,
                               alt_cal=False, alt_cnf=False, alt_eval=False):
        '''
        Create Testing Stage model folders.

        This method creates only the necessary folders without deleting existing ones.
        Use the phase-specific parameters for granular control.

        :param bcm_testing: If True, creates all Benchmark Model folders in Testing Stage
        :param alt_testing: If True, creates all Alternative Model folders in Testing Stage
        :param bcm_cal: If True, creates only BCM Fitting (CAL) folder
        :param bcm_cnf: If True, creates only BCM Prediction (CNF) folder
        :param bcm_eval: If True, creates only BCM Evaluation folder
        :param alt_cal: If True, creates only ALT Fitting (CAL) folder
        :param alt_cnf: If True, creates only ALT Prediction (CNF) folder
        :param alt_eval: If True, creates only ALT Evaluation folder
        '''
        folders = []

        # Benchmark Model - full or granular
        if bcm_testing:
            folders.extend([
                self.testing_benchmark_model,
                self.testing_benchmark_fitting,
                self.testing_benchmark_prediction,
                self.testing_benchmark_evaluation
            ])
        else:
            # Granular BCM folder creation
            if bcm_cal:
                folders.extend([self.testing_benchmark_model, self.testing_benchmark_fitting])
            if bcm_cnf:
                folders.extend([self.testing_benchmark_model, self.testing_benchmark_prediction])
            if bcm_eval:
                folders.extend([self.testing_benchmark_model, self.testing_benchmark_evaluation])

        # Alternative Model - full or granular
        if alt_testing:
            folders.extend([
                self.testing_alternative_model,
                self.testing_alternative_fitting,
                self.testing_alternative_prediction,
                self.testing_alternative_evaluation
            ])
        else:
            # Granular ALT folder creation
            if alt_cal:
                folders.extend([self.testing_alternative_model, self.testing_alternative_fitting])
            if alt_cnf:
                folders.extend([self.testing_alternative_model, self.testing_alternative_prediction])
            if alt_eval:
                folders.extend([self.testing_alternative_model, self.testing_alternative_evaluation])

        # Create all folders (without removing existing ones)
        for folder_path in folders:
            os.makedirs(folder_path, exist_ok=True)

    def create_application_models(self, bcm_application=False, alt_application=False,
                                    bcm_hrp=False, bcm_vp=False,
                                    alt_hrp=False, alt_vp=False):
        '''
        Create Application Stage model folders.

        This method creates only the necessary folders without deleting existing ones.
        Use the phase-specific parameters for granular control.

        :param bcm_application: If True, creates all Benchmark Model folders in Application Stage
        :param alt_application: If True, creates all Alternative Model folders in Application Stage
        :param bcm_hrp: If True, creates only BCM Fitting (HRP) folder
        :param bcm_vp: If True, creates only BCM Prediction (VP) folder
        :param alt_hrp: If True, creates only ALT Fitting (HRP) folder
        :param alt_vp: If True, creates only ALT Prediction (VP) folder
        '''
        folders = []

        # Benchmark Model - full or granular
        if bcm_application:
            folders.extend([
                self.application_benchmark_model,
                self.application_benchmark_fitting,
                self.application_benchmark_prediction
            ])
        else:
            # Granular BCM folder creation
            if bcm_hrp:
                folders.extend([self.application_benchmark_model, self.application_benchmark_fitting])
            if bcm_vp:
                folders.extend([self.application_benchmark_model, self.application_benchmark_prediction])

        # Alternative Model - full or granular
        if alt_application:
            folders.extend([
                self.application_alternative_model,
                self.application_alternative_fitting,
                self.application_alternative_prediction
            ])
        else:
            # Granular ALT folder creation
            if alt_hrp:
                folders.extend([self.application_alternative_model, self.application_alternative_fitting])
            if alt_vp:
                folders.extend([self.application_alternative_model, self.application_alternative_prediction])

        # Create all folders (without removing existing ones)
        for folder_path in folders:
            os.makedirs(folder_path, exist_ok=True)

    def get_all_paths(self):
        '''
        Get dictionary with all possible folder paths.

        Returns ALL potential paths in the VT7 folder structure, regardless of whether
        they were created or not. This is useful for documentation, path reference,
        or when you need to know all possible locations.

        :return: dictionary with folder names as keys and paths as values
        '''
        return {
            # Base paths
            'testing_stage': self.testing_stage,
            'application_stage': self.application_stage,

            # Testing stage - Benchmark Model
            'testing_benchmark_model': os.path.join(self.testing_stage, '1_Benchmark Model'),
            'testing_benchmark_fitting': os.path.join(self.testing_stage, '1_Benchmark Model', '1_Fitting Phase (CAL)'),
            'testing_benchmark_prediction': os.path.join(self.testing_stage, '1_Benchmark Model', '2_Prediction Phase (CNF)'),

            # Testing stage - Alternative Model
            'testing_alternative_model': os.path.join(self.testing_stage, '2_Alternative Model'),
            'testing_alternative_fitting': os.path.join(self.testing_stage, '2_Alternative Model', '1_Fitting Phase (CAL)'),
            'testing_alternative_prediction': os.path.join(self.testing_stage, '2_Alternative Model', '2_Prediction Phase (CNF)'),

            # Application stage - Benchmark Model
            'application_benchmark_model': os.path.join(self.application_stage, '1_Benchmark Model'),
            'application_benchmark_fitting': os.path.join(self.application_stage, '1_Benchmark Model', '1_Fitting Phase (HRP)'),
            'application_benchmark_prediction': os.path.join(self.application_stage, '1_Benchmark Model', '2_Prediction Phase (VP)'),

            # Application stage - Alternative Model
            'application_alternative_model': os.path.join(self.application_stage, '2_Alternative Model'),
            'application_alternative_fitting': os.path.join(self.application_stage, '2_Alternative Model', '1_Fitting Phase (HRP)'),
            'application_alternative_prediction': os.path.join(self.application_stage, '2_Alternative Model', '2_Prediction Phase (VP)')
        }
