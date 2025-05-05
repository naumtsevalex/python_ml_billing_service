import sys
import traceback
from typing import Optional

def format_error(error: Exception, additional_info: Optional[str] = None) -> str:
    """
    Форматирует информацию об ошибке в удобочитаемый вид.
    
    Args:
        error: Исключение, которое произошло
        additional_info: Дополнительная информация об ошибке (опционально)
    
    Returns:
        str: Отформатированное сообщение об ошибке
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()
    error_msg = []
    
    if additional_info:
        error_msg.append(f"{additional_info}: {str(error)}")
    else:
        error_msg.append(f"Error: {str(error)}")
        
    error_msg.extend([
        f"Type: {exc_type.__name__}",
        f"File: {exc_traceback.tb_frame.f_code.co_filename}",
        f"Line: {exc_traceback.tb_lineno}",
        f"Function: {exc_traceback.tb_frame.f_code.co_name}",
        f"Full traceback:\n{traceback.format_exc()}"
    ])
    
    return "\n".join(error_msg) 