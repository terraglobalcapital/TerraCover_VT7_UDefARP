# coding=utf-8
# ------------------------------------------------------------------------
#
#   Copyright:          © Terra Global Capital. All rights reserved.
#   Author:             david.montoya@terraglobalcapital.com
#   Python version:     3.11
#   Year:               2025
#
#   VT0007 UDef-ARP Standalone Version
#   Simplified base_processor with only required components
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------


from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Any
import os
from .progress_utils import safe_update_progress
from .message_boxes import _show_error_messagebox


# ------------------------------------------------------------------------


class BaseProcessor(ABC):
    """
    Abstract base class for TerraCover processing modules.

    Provides standardized:
    - Progress tracking and reporting
    - Cancel flag support
    - Input validation framework
    - Generic run method with consistent behavior
    """

    def __init__(self, progress_callback: Optional[Callable] = None, cancel_flag: Optional[Callable] = None,
                 show_progress: bool = True):
        """
        Initialize the base processor.

        Args:
            progress_callback (Callable, optional): Callback function for progress updates.
                                                   Should accept (message: str, percent: float)
            cancel_flag (Callable, optional): Function to check if operation should be cancelled.
                                            Should return True to cancel, False to continue.
            show_progress (bool): Whether to display progress messages during processing.
        """
        self.progress_callback = progress_callback
        self.cancel_flag = cancel_flag
        self.show_progress = show_progress
        self._validation_errors = []

    def _update_progress(self, message: str, percent: float) -> None:
        """
        Standard progress update method.

        Args:
            message (str): Progress message to display
            percent (float): Progress as decimal (0.0 to 1.0)
        """
        safe_update_progress(message, percent, self.progress_callback)

    def _check_cancellation(self) -> bool:
        """
        Check if operation should be cancelled.

        Returns:
            bool: True if operation should be cancelled
        """
        return self.cancel_flag and self.cancel_flag()

    def _check_cancellation_with_error(self, errors: List[str], message: str = "Operation cancelled by user") -> bool:
        """
        Check for cancellation and append error message if cancelled.

        Args:
            errors (List[str]): List to append cancellation error to
            message (str): Error message to append if cancelled

        Returns:
            bool: True if operation was cancelled (and error was added)
        """
        if self._check_cancellation():
            errors.append(message)
            return True
        return False

    @abstractmethod
    def _validation(self) -> List[str]:
        """
        Validate all inputs for the processor.

        Must be implemented by subclasses to provide comprehensive input validation.

        Returns:
            List[str]: List of validation error messages. Empty if no errors.
        """
        pass

    @abstractmethod
    def _process(self) -> Any:
        """
        Core processing logic.

        Must be implemented by subclasses to perform the actual processing work.

        Returns:
            Any: Processing result (file path, list of paths, etc.)
        """
        pass

    def run(self, show_progress: bool = True, validate_inputs: bool = True) -> Any:
        """
        Generic run method with standardized validation, progress tracking, and error handling.

        Args:
            show_progress (bool): Whether to show progress messages
            validate_inputs (bool): Whether to validate inputs before processing

        Returns:
            Any: Result from _process() method, or None if cancelled/failed
        """
        try:
            effective_show_progress = getattr(self, 'show_progress', show_progress)

            if effective_show_progress:
                self._update_progress(f"Starting {self.__class__.__name__} validation", 0.05)

            if self._check_cancellation():
                if effective_show_progress:
                    self._update_progress("Operation cancelled by user", 0.0)
                raise RuntimeError("Operation cancelled by user")

            if validate_inputs:
                validation_errors = self._validation()
                if validation_errors:
                    _show_error_messagebox(validation_errors)
                    print("Validation errors found:")
                    for error in validation_errors:
                        print(f"  - {error}")
                    if effective_show_progress:
                        self._update_progress("Validation failed", 0.0)
                    return None

            if effective_show_progress:
                self._update_progress("Validation completed successfully", 0.15)

            if self._check_cancellation():
                if effective_show_progress:
                    self._update_progress("Operation cancelled by user", 0.0)
                raise RuntimeError("Operation cancelled by user")

            if effective_show_progress:
                self._update_progress("Starting processing", 0.20)

            result = self._process()

            if effective_show_progress:
                self._update_progress("Processing completed successfully", 1.0)

            return result

        except RuntimeError as e:
            if "cancelled" in str(e).lower():
                print(f"Operation cancelled")
                return None
            else:
                if effective_show_progress:
                    self._update_progress(f"Error: {str(e)}", 0.0)
                raise
        except Exception as e:
            if not hasattr(e, '_already_handled'):
                error_msg = f"Error during {self.__class__.__name__}: {str(e)}"
                print(error_msg)
                if effective_show_progress:
                    self._update_progress(error_msg, 0.0)
            raise


class BaseFileProcessor(BaseProcessor):
    """
    Base class for processors that handle file operations.

    Provides standardized methods for:
    - Single file processing
    - File output generation with suffixes
    """

    def __init__(self, input_file=None, input_files=None, output_file=None, suffix="",
                 show_progress: bool = True, progress_callback: Optional[Callable] = None, cancel_flag: Optional[Callable] = None):
        """
        Initialize the file processor.

        Args:
            input_file (str, optional): Single input file path
            input_files (List[str], optional): List of input file paths for batch processing
            output_file (str, optional): Output file path
            suffix (str): Suffix to add to output filenames
            show_progress (bool): Whether to display progress messages during processing
            progress_callback (Callable, optional): Progress callback function
            cancel_flag (Callable, optional): Cancellation check function
        """
        super().__init__(progress_callback, cancel_flag, show_progress)
        self.input_file = input_file
        self.input_files = input_files
        self.suffix = suffix
        self._original_output_file = output_file
        self._setup_output_paths(output_file)

    def _setup_output_paths(self, output_file):
        """
        Setup output file and folder paths based on input configuration.

        Args:
            output_file (str, optional): Output file path or folder path
        """
        if output_file is not None and output_file != "":
            if self.input_file:
                self.output_file = output_file
                self.output_folder = os.path.dirname(self.output_file)
            else:
                self.output_file = output_file
                self.output_folder = os.path.dirname(output_file) if output_file else None
        else:
            if self.input_file:
                self.output_folder = os.path.dirname(self.input_file)
                self.output_file = None
            else:
                self.output_folder = None
                self.output_file = None

    def _process(self) -> str:
        """
        Main processing method for single file processing.

        Returns:
            str: Single file path
        """
        if self.input_file is not None and self.input_file != "":
            return self._process_single()
        else:
            raise ValueError("input_file must be provided")

    @abstractmethod
    def _process_single(self) -> str:
        """
        Process a single file using the current instance variables.
        Must be implemented by subclasses to provide specific processing logic.

        Returns:
            str: Path to output file
        """
        pass
