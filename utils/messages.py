from typing import Optional, Dict, Any

def format_success_message(title: str, message: str = "", details: Optional[Dict[str, Any]] = None) -> str:
    result = f"✅ <b>{title}</b>"
    if message:
        result += f"\n\n{message}"
    if details:
        details_text = "\n".join([f"• {k}: {v}" for k, v in details.items()])
        result += f"\n\n{details_text}"
    return result

def format_error_message(title: str, message: str = "", suggestion: str = "") -> str:
    result = f"❌ <b>{title}</b>"
    if message:
        result += f"\n\n{message}"
    if suggestion:
        result += f"\n\n💡 {suggestion}"
    return result

def format_info_message(title: str, message: str = "") -> str:
    result = f"ℹ️ <b>{title}</b>"
    if message:
        result += f"\n\n{message}"
    return result

def format_warning_message(title: str, message: str = "") -> str:
    result = f"⚠️ <b>{title}</b>"
    if message:
        result += f"\n\n{message}"
    return result

