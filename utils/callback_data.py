from typing import Optional, Tuple
from datetime import datetime

class CallbackData:
    @staticmethod
    def create_order_date(date: datetime) -> str:
        return f"order_date_{date.strftime('%Y-%m-%d')}"
    
    @staticmethod
    def parse_order_date(callback_data: str) -> Optional[datetime]:
        if not callback_data.startswith("order_date_"):
            return None
        try:
            date_str = callback_data.replace("order_date_", "")
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None
    
    @staticmethod
    def create_category(category: str, date_str: str) -> str:
        return f"category_{category}_{date_str}"
    
    @staticmethod
    def parse_category(callback_data: str) -> Optional[Tuple[str, str]]:
        if not callback_data.startswith("category_"):
            return None
        try:
            parts = callback_data.split("_")
            if len(parts) < 3:
                return None
            category = "_".join(parts[1:-1])
            date_str = parts[-1]
            return category, date_str
        except Exception:
            return None
    
    @staticmethod
    def create_dish(dish_id: int, date_str: str) -> str:
        return f"dish_{dish_id}_{date_str}"
    
    @staticmethod
    def parse_dish(callback_data: str) -> Optional[Tuple[int, str]]:
        if not callback_data.startswith("dish_"):
            return None
        try:
            parts = callback_data.split("_")
            if len(parts) < 3:
                return None
            dish_id = int(parts[1])
            date_str = parts[2]
            return dish_id, date_str
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def create_admin_order(order_id: int) -> str:
        return f"admin_order_{order_id}"
    
    @staticmethod
    def parse_admin_order(callback_data: str) -> Optional[int]:
        if not callback_data.startswith("admin_order_"):
            return None
        try:
            return int(callback_data.replace("admin_order_", ""))
        except ValueError:
            return None
    
    @staticmethod
    def create_admin_dish(dish_id: int) -> str:
        return f"admin_dish_{dish_id}"
    
    @staticmethod
    def parse_admin_dish(callback_data: str) -> Optional[int]:
        if not callback_data.startswith("admin_dish_"):
            return None
        try:
            return int(callback_data.replace("admin_dish_", ""))
        except ValueError:
            return None
    
    @staticmethod
    def create_order_details(order_id: int) -> str:
        return f"order_details_{order_id}"
    
    @staticmethod
    def parse_order_details(callback_data: str) -> Optional[int]:
        if not callback_data.startswith("order_details_"):
            return None
        try:
            return int(callback_data.replace("order_details_", ""))
        except ValueError:
            return None
    
    @staticmethod
    def create_cancel_order(order_id: int) -> str:
        return f"cancel_order_{order_id}"
    
    @staticmethod
    def parse_cancel_order(callback_data: str) -> Optional[int]:
        if not callback_data.startswith("cancel_order_"):
            return None
        try:
            return int(callback_data.replace("cancel_order_", ""))
        except ValueError:
            return None
    
    @staticmethod
    def create_edit_order(order_id: int) -> str:
        return f"edit_order_{order_id}"
    
    @staticmethod
    def parse_edit_order(callback_data: str) -> Optional[int]:
        if not callback_data.startswith("edit_order_"):
            return None
        try:
            return int(callback_data.replace("edit_order_", ""))
        except ValueError:
            return None
    
    @staticmethod
    def create_remove_item(order_id: int, item_id: int) -> str:
        return f"remove_item_{order_id}_{item_id}"
    
    @staticmethod
    def parse_remove_item(callback_data: str) -> Optional[Tuple[int, int]]:
        if not callback_data.startswith("remove_item_"):
            return None
        try:
            parts = callback_data.split("_")
            if len(parts) < 4:
                return None
            order_id = int(parts[2])
            item_id = int(parts[3])
            return order_id, item_id
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def create_admin_order_status(order_id: int, status: str) -> str:
        return f"admin_order_status_{order_id}_{status}"
    
    @staticmethod
    def parse_admin_order_status(callback_data: str) -> Optional[Tuple[int, str]]:
        if not callback_data.startswith("admin_order_status_"):
            return None
        try:
            parts = callback_data.replace("admin_order_status_", "").split("_")
            if len(parts) < 2:
                return None
            order_id = int(parts[0])
            status = parts[1]
            return order_id, status
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def create_delete_dish_confirm(dish_id: int) -> str:
        return f"delete_dish_confirm_{dish_id}"
    
    @staticmethod
    def parse_delete_dish_confirm(callback_data: str) -> Optional[int]:
        if not callback_data.startswith("delete_dish_confirm_"):
            return None
        try:
            return int(callback_data.replace("delete_dish_confirm_", ""))
        except ValueError:
            return None

