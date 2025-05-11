import hashlib

# 用于生成安全ID的盐值
_Z1_GRAY_SALT = "DEFINE_A_TRULY_UNIQUE_AND_SECRET_SALT_HERE_vXYZ"

def generate_user_secure_id(user_id: int) -> str:
    """
    根据用户ID生成安全标识符
    
    Args:
        user_id: 用户的Telegram ID
        
    Returns:
        生成的16位安全标识符字符串
    """
    # 拼接user_id和盐值
    combined_string = f"{user_id}_{_Z1_GRAY_SALT}"
    
    # 使用UTF-8编码并计算SHA-256哈希
    hash_object = hashlib.sha256(combined_string.encode('utf-8'))
    
    # 获取哈希的十六进制表示，并返回前16个字符
    return hash_object.hexdigest()[:16]
