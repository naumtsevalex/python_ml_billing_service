import sys
from datetime import datetime
from db.database import Database
from models.user import User
from models.balance import Balance
from models.task import Task

class BillingService:
    """Простой сервис для работы с балансом пользователей в боте"""
    
    def __init__(self):
        self.db = Database()
    
    async def check_user_balance(self, user_id: int) -> tuple[bool, str, float]:
        """
        Проверяет баланс пользователя и возвращает можно ли выполнять операцию
        
        Args:
            user_id: ID пользователя
            
        Returns:
            tuple: (можно_выполнять_операцию, сообщение, текущий_баланс)
        """
        # Получаем баланс пользователя
        balance = await self.db.get_balance_object(user_id)
        
        if not balance:
            return False, "Ошибка: баланс не найден.", 0
        
        # По условию, если баланс > 0, разрешаем операцию
        if balance.balance > 0:
            return True, "Баланс положительный, операция разрешена.", balance.balance
        else:
            return False, f"⚠️ Недостаточно средств. Ваш баланс: {balance.balance} кредитов.", balance.balance
    
    async def get_balance_info(self, user_id: int) -> str:
        """
        Получает информацию о балансе пользователя в текстовом формате
        
        Args:
            user_id: ID пользователя
            
        Returns:
            str: Форматированная строка с информацией о балансе
        """
        balance = await self.db.get_balance_object(user_id)
        
        if not balance:
            return "Ошибка: баланс не найден."
        
        last_updated = balance.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        return f"💰 Ваш текущий баланс: {balance.balance} кредитов\n📊 Последнее обновление: {last_updated}"
    
    async def _update_balance(self, user_id: int, amount: float, reason: str = None) -> Balance:
        """
        Обновляет баланс пользователя
        
        Args:
            user_id: ID пользователя
            amount: Сумма изменения (положительная - пополнение, отрицательная - списание)
            reason: Причина изменения баланса
            
        Returns:
            tuple: (успешно, сообщение)
        """
        # Получаем текущий баланс
        old_balance = await self.db.get_balance_object(user_id)
        if not old_balance:
            return False, "Ошибка: баланс не найден."
        
        # Обновляем баланс
        await self.db.update_balance(user_id, amount)
        
        # Логируем транзакцию
        await self.db.log(
            user_id=user_id,
            action="BALANCE_UPDATE",
            details=f"Amount: {amount}, Reason: {reason}, Previous balance: {old_balance.balance}"
        )
        
        # Получаем обновленный баланс
        new_balance = await self.db.get_balance_object(user_id)
        
        return new_balance
                
    async def charge_for_task(self, task_id: str, reason: str = None) -> tuple[Task, Balance]:
        """
        Списывает средства с баланса пользователя за выполнение задачи
        
        Args:
            task_id: ID задачи
            reason: Причина списания средств
            
        Returns:
            tuple: (успешно, сообщение)
        """
        # Получаем задачу по ID
        task = await self.db.get_task(task_id)
        if not task:
            return False, "Ошибка: задача не найдена."
        
        # Получаем ID пользователя и стоимость из задачи
        user_id = task.user_id
        cost = task.cost
        
        # Списываем средства с баланса пользователя
        if not reason:
            reason = f"Оплата задачи {task_id}"
        
        # Отрицательное значение для списания
        return task, await self._update_balance(user_id, -cost, reason)
    
    def str_report_balance(self, balance: Balance) -> tuple[bool, str]:
        """
        Отправляет сообщение о балансе пользователю
        """
        if balance.balance <= 0:
            return False, f"⚠️ Недостаточно средств. Ваш баланс: {balance.balance} кредитов.\nДля пополнения баланса используй команду /balance"
        else:
            return True, f"💰 Ваш текущий баланс: {balance.balance} кредитов."