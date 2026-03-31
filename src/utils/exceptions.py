class GraphIRException(Exception):
    """项目基础异常。"""


class ParseError(GraphIRException):
    """解析错误。"""


class ValidationError(GraphIRException):
    """校验错误。"""
