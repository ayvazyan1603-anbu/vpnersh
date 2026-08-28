import urllib.parse

class QRService:
    @staticmethod
    def get_qr_url(data: str) -> str:
        """Возвращает URL изображения QR-кода для любого текста / ссылки"""
        encoded_data = urllib.parse.quote_plus(data)
        return f"https://api.qrserver.com/v1/create-qr-code/?size=350x350&data={encoded_data}"
