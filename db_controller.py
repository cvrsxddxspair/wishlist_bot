import sqlite3
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

DB_NAME = 'wishlist.db'


def get_connection():
    """Получить соединение с БД"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализировать БД и создать таблицы"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица групп
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS "group" (
            group_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT
        )
    ''')
    
    # Таблица членов группы
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_member (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (group_id) REFERENCES "group"(group_id),
            FOREIGN KEY (user_id) REFERENCES user(user_id),
            UNIQUE(group_id, user_id)
        )
    ''')
    
    # Таблица желаний
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wish (
            wish_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            wish_text TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            priority INTEGER DEFAULT 3,
            create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            complete_date TIMESTAMP,
            image_url TEXT,
            price REAL,
            FOREIGN KEY (user_id) REFERENCES user(user_id)
        )
    ''')
    
    # Таблица резервирований
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reservation (
            reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            wish_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reserved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'reserved',
            FOREIGN KEY (wish_id) REFERENCES wish(wish_id),
            FOREIGN KEY (user_id) REFERENCES user(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()


# ============== USER функции ==============

def add_user(user_id: int, username: Optional[str] = None, 
             first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
    """Добавить нового пользователя"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO user (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Получить информацию о пользователе"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Получить информацию о пользователе по username"""
    # Убираем @ если присутствует
    if username.startswith('@'):
        username = username[1:]
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM user WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def user_exists(user_id: int) -> bool:
    """Проверить, существует ли пользователь"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM user WHERE user_id = ?', (user_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def update_user(user_id: int, username: Optional[str] = None,
                first_name: Optional[str] = None, last_name: Optional[str] = None) -> bool:
    """Обновить информацию о пользователе"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if username is not None:
            updates.append('username = ?')
            params.append(username)
        if first_name is not None:
            updates.append('first_name = ?')
            params.append(first_name)
        if last_name is not None:
            updates.append('last_name = ?')
            params.append(last_name)
        
        if not updates:
            conn.close()
            return False
        
        params.append(user_id)
        query = f'UPDATE user SET {", ".join(updates)} WHERE user_id = ?'
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


# ============== WISH функции ==============

def add_wish(user_id: int, chat_id: int, wish_text: str, 
             description: Optional[str] = None, priority: int = 3,
             image_url: Optional[str] = None, price: Optional[float] = None) -> Optional[int]:
    """Добавить новое желание. Возвращает ID желания"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO wish (user_id, chat_id, wish_text, description, priority, image_url, price)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, chat_id, wish_text, description, priority, image_url, price))
        wish_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return wish_id
    except Exception:
        conn.close()
        return None


def get_wish(wish_id: int) -> Optional[Dict[str, Any]]:
    """Получить информацию о желании"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM wish WHERE wish_id = ?', (wish_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_wishes(user_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Получить все желания пользователя. Если status задан, то только с этим статусом"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if status:
        cursor.execute('SELECT * FROM wish WHERE user_id = ? AND status = ? ORDER BY create_date DESC', 
                      (user_id, status))
    else:
        cursor.execute('SELECT * FROM wish WHERE user_id = ? ORDER BY create_date DESC', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_chat_wishes(chat_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Получить все желания в чате"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if status:
        cursor.execute('SELECT * FROM wish WHERE chat_id = ? AND status = ? ORDER BY priority DESC, create_date DESC',
                      (chat_id, status))
    else:
        cursor.execute('SELECT * FROM wish WHERE chat_id = ? ORDER BY priority DESC, create_date DESC', (chat_id,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_wish(wish_id: int, wish_text: Optional[str] = None,
                description: Optional[str] = None, status: Optional[str] = None,
                priority: Optional[int] = None, price: Optional[float] = None) -> bool:
    """Обновить информацию о желании"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if wish_text is not None:
            updates.append('wish_text = ?')
            params.append(wish_text)
        if description is not None:
            updates.append('description = ?')
            params.append(description)
        if status is not None:
            updates.append('status = ?')
            params.append(status)
        if priority is not None:
            updates.append('priority = ?')
            params.append(priority)
        if price is not None:
            updates.append('price = ?')
            params.append(price)
        
        if not updates:
            conn.close()
            return False
        
        params.append(wish_id)
        query = f'UPDATE wish SET {", ".join(updates)} WHERE wish_id = ?'
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def complete_wish(wish_id: int) -> bool:
    """Отметить желание как выполненное"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE wish SET status = 'completed', complete_date = CURRENT_TIMESTAMP
            WHERE wish_id = ?
        ''', (wish_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def cancel_wish(wish_id: int) -> bool:
    """Отменить желание"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE wish SET status = ? WHERE wish_id = ?', ('cancelled', wish_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def delete_wish(wish_id: int) -> bool:
    """Удалить желание"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM wish WHERE wish_id = ?', (wish_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


# ============== GROUP функции ==============

def add_group(group_id: int, title: str, description: Optional[str] = None) -> bool:
    """Добавить новую группу"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO "group" (group_id, title, description)
            VALUES (?, ?, ?)
        ''', (group_id, title, description))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def get_group(group_id: int) -> Optional[Dict[str, Any]]:
    """Получить информацию о группе"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM "group" WHERE group_id = ?', (group_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def group_exists(group_id: int) -> bool:
    """Проверить, существует ли группа"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM "group" WHERE group_id = ?', (group_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def update_group(group_id: int, title: Optional[str] = None,
                 description: Optional[str] = None) -> bool:
    """Обновить информацию о группе"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if title is not None:
            updates.append('title = ?')
            params.append(title)
        if description is not None:
            updates.append('description = ?')
            params.append(description)
        
        if not updates:
            conn.close()
            return False
        
        params.append(group_id)
        query = f'UPDATE "group" SET {", ".join(updates)} WHERE group_id = ?'
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def delete_group(group_id: int) -> bool:
    """Удалить группу"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM "group" WHERE group_id = ?', (group_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


# ============== GROUP_MEMBER функции ==============

def add_group_member(group_id: int, user_id: int) -> bool:
    """Добавить пользователя в группу"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO group_member (group_id, user_id)
            VALUES (?, ?)
        ''', (group_id, user_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def remove_group_member(group_id: int, user_id: int) -> bool:
    """Удалить пользователя из группы"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM group_member WHERE group_id = ? AND user_id = ?
        ''', (group_id, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def get_group_members(group_id: int) -> List[int]:
    """Получить список ID пользователей в группе"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM group_member WHERE group_id = ?', (group_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def get_user_groups(user_id: int) -> List[int]:
    """Получить список ID групп, в которых состоит пользователь"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT group_id FROM group_member WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def is_group_member(group_id: int, user_id: int) -> bool:
    """Проверить, является ли пользователь членом группы"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM group_member WHERE group_id = ? AND user_id = ?', 
                   (group_id, user_id))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


# ============== RESERVATION функции ==============

def add_reservation(wish_id: int, user_id: int) -> Optional[int]:
    """Добавить резервирование. Возвращает ID резервирования"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reservation (wish_id, user_id, status)
            VALUES (?, ?, 'reserved')
        ''', (wish_id, user_id))
        reservation_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return reservation_id
    except Exception:
        conn.close()
        return None


def get_reservation(reservation_id: int) -> Optional[Dict[str, Any]]:
    """Получить информацию о резервировании"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reservation WHERE reservation_id = ?', (reservation_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_wish_reservations(wish_id: int) -> List[Dict[str, Any]]:
    """Получить все резервирования для желания"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reservation WHERE wish_id = ? ORDER BY reserved_at DESC', (wish_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_user_reservations(user_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Получить все резервирования пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if status:
        cursor.execute('SELECT * FROM reservation WHERE user_id = ? AND status = ? ORDER BY reserved_at DESC',
                      (user_id, status))
    else:
        cursor.execute('SELECT * FROM reservation WHERE user_id = ? ORDER BY reserved_at DESC', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_active_reservation_for_wish(wish_id: int) -> Optional[Dict[str, Any]]:
    """Получить активное резервирование для желания"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reservation WHERE wish_id = ? AND status = ?', 
                   (wish_id, 'reserved'))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_reservation_status(reservation_id: int, status: str) -> bool:
    """Обновить статус резервирования (reserved, cancelled, fulfilled)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE reservation SET status = ? WHERE reservation_id = ?', 
                       (status, reservation_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def cancel_reservation(reservation_id: int) -> bool:
    """Отменить резервирование"""
    return update_reservation_status(reservation_id, 'cancelled')


def fulfill_reservation(reservation_id: int) -> bool:
    """Отметить резервирование как выполненное"""
    return update_reservation_status(reservation_id, 'fulfilled')


def delete_reservation(reservation_id: int) -> bool:
    """Удалить резервирование"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM reservation WHERE reservation_id = ?', (reservation_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False
