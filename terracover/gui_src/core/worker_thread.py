# coding=utf-8
# ------------------------------------------------------------------------
#
#   Copyright:          © Terra Global Capital. All rights reserved.
#   Author:             david.montoya@terraglobalcapital.com
#   Python version:     3.11
#   GDAL version:       3.10.3
#   GeoPandas version:  1.1.1
#   PyQt6 version:      6.7.1
#   Year:               2025
#
#   This code is proprietary and confidential.
#   Unauthorized copying or distribution is prohibited.
#
# ------------------------------------------------------------------------


"""
Worker thread for running analysis functions in the background
"""

from PyQt6.QtCore import QThread, pyqtSignal
import traceback


class WorkerThread(QThread):
    """Worker thread for running analysis functions in the background"""
    progress_updated = pyqtSignal(str, float)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, analysis_function, **kwargs):
        super().__init__()
        self.analysis_function = analysis_function
        self.kwargs = kwargs
        self.cancelled = False
    
    def cancel(self):
        """Cancel the operation"""
        self.cancelled = True
    
    def check_cancel(self):
        """Check if operation should be cancelled"""
        return self.cancelled
    
    def update_progress(self, message, percent):
        """Update progress callback"""
        self.progress_updated.emit(message, percent)
    
    def run(self):
        """Run the analysis function"""
        try:
            # Add progress callback and cancel flag to kwargs
            self.kwargs['progress_callback'] = self.update_progress
            self.kwargs['cancel_flag'] = self.check_cancel
            
            # Run the analysis
            result = self.analysis_function(**self.kwargs)
            
            if self.cancelled:
                self.finished.emit(False, "Analysis cancelled by user")
            elif result is None or result is False:
                # Analysis function returned None or False, which indicates validation failure or other issue
                self.finished.emit(False, "Analysis failed - validation errors or processing issues occurred")
            else:
                self.finished.emit(True, "Analysis completed successfully")
                
        except InterruptedError as e:
            # User cancelled the operation - don't show traceback
            self.finished.emit(False, str(e))
        except Exception as e:
            # For Python Console errors (already handled), just show the simple error message
            if hasattr(e, '_already_handled'):
                # Simple error message without traceback
                error_msg = f"Analysis failed: {str(e)}"
            else:
                # Format error message with more user-friendly details
                error_msg = self._format_error_message(e)
            self.finished.emit(False, error_msg)

    def _format_error_message(self, e: Exception) -> str:
        """
        Format error message to be user-friendly while providing relevant technical details.

        Args:
            e: The exception to format

        Returns:
            Formatted error message string
        """
        import os

        # Extract the main error message
        error_str = str(e)

        # Check if error message is already well-formatted (multi-line with clear explanation)
        # Well-formatted messages typically have multiple lines with helpful context
        if "\n" in error_str and any(keyword in error_str.lower() for keyword in [
            "common issues:", "please ensure", "invalid values found:", "must be", "required"
        ]):
            # Error message is already clear and user-friendly - don't add traceback
            return error_str

        # Check for common error types and provide user-friendly messages
        if "Permission denied" in error_str or "PermissionError" in str(type(e)):
            # Extract filename from error message
            if ":" in error_str and ("/" in error_str or "\\" in error_str):
                # Try to extract the file path
                parts = error_str.split("'")
                if len(parts) >= 2:
                    file_path = parts[1]
                    file_name = os.path.basename(file_path)
                    return (f"Cannot access file because it is currently open in another program.\n\n"
                           f"File: {file_name}\n\n"
                           f"Please close the file and try again.\n\n"
                           f"Full path: {file_path}")
            return f"Permission denied: {error_str}\n\nThe file may be open in another program. Please close it and try again."

        elif "FileNotFoundError" in str(type(e)) or "No such file" in error_str:
            return f"File not found: {error_str}"

        elif "RuntimeError" in str(type(e)) and "Failed to save Excel file" in error_str:
            # This is our custom RuntimeError from _SaveTable
            return error_str  # Already has a clear message

        else:
            # For other errors, show the error with minimal traceback
            tb = traceback.format_exc()
            # Get just the last few lines of traceback (the most relevant part)
            tb_lines = tb.split('\n')
            # Find the line with "raise" or the actual error
            relevant_lines = []
            for i, line in enumerate(tb_lines):
                if 'File "' in line:
                    # Include this line and the next one (the code line)
                    relevant_lines.append(line)
                    if i + 1 < len(tb_lines):
                        relevant_lines.append(tb_lines[i + 1])

            # Get last error line
            error_line = tb_lines[-1] if tb_lines else str(e)

            if relevant_lines:
                # Show last 2 stack frames plus error
                last_frames = '\n'.join(relevant_lines[-4:]) if len(relevant_lines) >= 4 else '\n'.join(relevant_lines)
                return f"Error during analysis: {error_str}\n\nRelevant traceback:\n{last_frames}\n{error_line}"
            else:
                return f"Error during analysis: {error_str}"