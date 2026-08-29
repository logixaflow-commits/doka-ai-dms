"""
Office DMS - Encryption Module
Fernet symmetric encryption for sensitive documents at rest.
"""
import os
import base64
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EncryptionManager:
    """Manages Fernet symmetric encryption for sensitive document content with multi-key support."""

    def __init__(self):
        self._fernet: Fernet = None  # Current encryption key (first in list)
        self._fernets: list[Fernet] = []  # All available keys for decryption
        self._key_ids: list[str] = []  # Key identifiers
        self._init_cipher()

    def _init_cipher(self):
        """Initialize Fernet ciphers from encryption keys (support key rotation)."""
        # Try ENCRYPTION_KEYS first (comma-separated list for key rotation)
        encryption_keys = os.getenv('ENCRYPTION_KEYS', '')
        
        if encryption_keys:
            # Multi-key mode for key rotation
            keys_list = [key.strip() for key in encryption_keys.split(',') if key.strip()]
            
            if not keys_list:
                logger.warning("ENCRYPTION_KEYS is empty, falling back to ENCRYPTION_KEY")
                self._init_single_key()
                return
                
            for idx, key in enumerate(keys_list):
                try:
                    fernet = self._create_fernet_from_key(key)
                    self._fernets.append(fernet)
                    self._key_ids.append(f"key_{idx}")
                    logger.debug(f"Loaded encryption key {idx + 1}/{len(keys_list)}")
                except Exception as e:
                    logger.error(f"Failed to load encryption key {idx}: {e}")
            
            if not self._fernets:
                logger.error("No valid encryption keys found")
                return
            
            # First key is used for encryption
            self._fernet = self._fernets[0]
            logger.info(f"Multi-key encryption initialized with {len(self._fernets)} keys (key rotation enabled)")
            
        else:
            # Single key mode (backward compatibility)
            self._init_single_key()

    def _init_single_key(self):
        """Initialize with single ENCRYPTION_KEY (backward compatibility)."""
        key = settings.ENCRYPTION_KEY
        if not key:
            logger.warning("ENCRYPTION_KEY not set. Encryption is DISABLED.")
            return

        try:
            fernet = self._create_fernet_from_key(key)
            self._fernet = fernet
            self._fernets = [fernet]
            self._key_ids = ["default"]
            logger.info("Single-key encryption initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize encryption cipher: {e}")
            self._fernet = None
            self._fernets = []

    def _create_fernet_from_key(self, key: str) -> Fernet:
        """Create a Fernet instance from a key string."""
        # If key is a valid Fernet key (32 bytes base64-encoded)
        if len(key) == 44:  # Standard Fernet key length in base64
            return Fernet(key.encode())
        else:
            # Derive key from password using PBKDF2
            return self._derive_key(key)

    def _derive_key(self, password: str) -> Fernet:
        """Derive a Fernet key from a password using PBKDF2."""
        salt = b"office_dms_static_salt_2024"  # In production, use per-file salt stored with file
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)

    @property
    def is_enabled(self) -> bool:
        """Check if encryption is enabled and initialized."""
        return self._fernet is not None

    @property
    def key_id(self) -> str:
        """Return current encryption key identifier."""
        return self._key_id

    def encrypt(self, data: bytes) -> bytes:
        """
        Encrypt raw bytes. Returns encrypted data.
        If encryption is disabled, returns data unchanged.
        """
        if not self.is_enabled:
            logger.debug("Encryption disabled, returning data as-is.")
            return data

        try:
            encrypted = self._fernet.encrypt(data)
            logger.debug(f"Encrypted {len(data)} bytes -> {len(encrypted)} bytes")
            return encrypted
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt data: {e}") from e

    def decrypt(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt encrypted bytes using available keys (supports key rotation).
        Returns original data.
        """
        if not self.is_enabled:
            return encrypted_data

        # Try each available key until one succeeds (for key rotation)
        for idx, fernet in enumerate(self._fernets):
            try:
                decrypted = fernet.decrypt(encrypted_data)
                logger.debug(f"Decrypted {len(encrypted_data)} bytes -> {len(decrypted)} bytes using key {idx}")
                return decrypted
            except Exception as e:
                if idx < len(self._fernets) - 1:
                    logger.debug(f"Key {idx} failed, trying next key...")
                    continue
                else:
                    logger.error(f"Decryption failed with all {len(self._fernets)} keys")
                    raise DecryptionError(f"Failed to decrypt data with all available keys") from e

    def encrypt_file(self, file_path: str, output_path: str) -> str:
        """
        Encrypt a file and write to output path.
        Returns the output path.
        """
        with open(file_path, "rb") as f:
            data = f.read()

        encrypted = self.encrypt(data)

        with open(output_path, "wb") as f:
            f.write(encrypted)

        logger.info(f"File encrypted: {file_path} -> {output_path}")
        return output_path

    def decrypt_file(self, encrypted_path: str, output_path: str) -> str:
        """
        Decrypt a file and write to output path.
        Returns the output path.
        """
        with open(encrypted_path, "rb") as f:
            encrypted_data = f.read()

        decrypted = self.decrypt(encrypted_data)

        with open(output_path, "wb") as f:
            f.write(decrypted)

        logger.info(f"File decrypted: {encrypted_path} -> {output_path}")
        return output_path

    def rotate_key(self, new_key: str):
        """Rotate encryption key (re-encrypt all sensitive documents)."""
        old_fernet = self._fernet
        try:
            # Create new cipher
            new_fernet = self._create_fernet_from_key(new_key)
            
            # Add new key to the front of the list (becomes primary for encryption)
            self._fernets.insert(0, new_fernet)
            self._key_ids.insert(0, f"new_key_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            self._fernet = new_fernet
            
            logger.info(f"Key rotation initiated. Total keys available: {len(self._fernets)}")
            # Implementation: iterate all encrypted docs, decrypt with old, encrypt with new
            # This would be implemented as a background task in production
            
        except Exception as e:
            logger.error(f"Key rotation failed: {e}")
            raise EncryptionError(f"Key rotation failed: {e}") from e

    def reencrypt_all_documents(self):
        """
        Re-encrypt all sensitive documents with the current primary key.
        This is useful after key rotation to ensure all documents use the latest key.
        
        In production, this would be run as a background task.
        """
        if not self.is_enabled or len(self._fernets) <= 1:
            logger.warning("Key rotation not needed - only one key available")
            return
        
        logger.info("Starting document re-encryption with latest key...")
        # Implementation would:
        # 1. Query all encrypted documents from database
        # 2. For each document:
        #    a. Decrypt with any available key (using decrypt method)
        #    b. Encrypt with current primary key (self._fernet)
        #    c. Update document in database
        # 4. Remove old keys from self._fernets and self._key_ids
        # This is a placeholder for the actual implementation
        logger.warning("Document re-encryption not implemented - requires database integration")


class EncryptionError(Exception):
    """Raised when encryption fails."""
    pass


class DecryptionError(Exception):
    """Raised when decryption fails."""
    pass


# Singleton
encryption_manager = EncryptionManager()
