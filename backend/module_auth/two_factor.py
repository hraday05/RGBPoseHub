"""
Module Auth — Two-Factor Authentication (TOTP)
Implements TOTP-based 2FA using PyOTP with QR code generation.
"""
import pyotp
import qrcode
import io
import base64


class TwoFactorAuth:
    """TOTP-based Two-Factor Authentication handler."""
    
    ISSUER_NAME = 'RGB-Pose Hub'
    
    @staticmethod
    def generate_secret():
        """Generate a new TOTP secret key."""
        return pyotp.random_base32()
    
    @staticmethod
    def get_totp(secret):
        """Get a TOTP instance from a secret."""
        return pyotp.TOTP(secret)
    
    @staticmethod
    def verify_otp(secret, otp_code):
        """
        Verify a TOTP code against the secret.
        Allows 1 time step tolerance (30 seconds before/after).
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(otp_code, valid_window=1)
    
    @staticmethod
    def get_provisioning_uri(secret, email):
        """Generate the provisioning URI for authenticator apps."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=email,
            issuer_name=TwoFactorAuth.ISSUER_NAME
        )
    
    @staticmethod
    def generate_qr_code_base64(provisioning_uri):
        """
        Generate a QR code image for the provisioning URI.
        Returns a base64-encoded PNG string.
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    @staticmethod
    def get_current_otp(secret):
        """Get the current OTP code (useful for testing)."""
        totp = pyotp.TOTP(secret)
        return totp.now()
