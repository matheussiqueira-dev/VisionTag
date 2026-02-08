class VisionTagError(Exception):
    """Base para erros de dominio da aplicacao."""


class InputValidationError(VisionTagError):
    """Erro de validacao de entrada."""


class AuthenticationError(VisionTagError):
    """Erro de autenticacao/autorizacao."""


class ModelInferenceError(VisionTagError):
    """Erro durante inferencia no modelo de visao."""

