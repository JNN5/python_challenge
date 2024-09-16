from dataclasses import dataclass
import json


@dataclass
class ApiGwResponse:
    isBase64Encoded: bool
    statusCode: int
    headers: dict[str, any]
    body: str

    def __init__(
        self,
        statusCode: int,
        body: str = "",
        cors=None,
        is_base64_encoded: bool = False,
    ):
        self.statusCode = statusCode
        self.body = body if isinstance(body, str) else json.dumps(body)
        self.headers = self._generate_secure_headers(cors)
        self.isBase64Encoded = is_base64_encoded

    def _generate_secure_headers(self, cors):
        headers = {}
        headers["Content-Type"] = "application/json"
        headers["X-Content-Type-Options"] = "nosniff"
        headers["Strict-Transport-Security"] = "max-age=16070400; includeSubDomains"
        headers["X-XSS-Protection"] = "1; mode=block"
        headers["X-Frame-Options"] = "SAMEORIGIN"
        headers["Cache-Control"] = "no-store"
        headers["content-security-policy"] = "default-src 'self'; object-src 'none';"
        headers["x-permitted-cross-domain-policies"] = "master-only"
        if cors is not None:
            headers["Access-Control-Allow-Origin"] = cors
        return headers

    def to_json(self):
        return self.__dict__
