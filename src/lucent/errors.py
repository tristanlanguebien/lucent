class LucentConventionNotFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)


class LucentRuleNotFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)


class LucentRecursionError(Exception):
    def __init__(self, message):
        super().__init__(message)


class LucentMissingFieldsError(Exception):
    def __init__(self, message):
        super().__init__(message)


class LucentMissingEnvironmentVariablesError(Exception):
    def __init__(self, message):
        super().__init__(message)


class LucentFieldValueError(Exception):
    def __init__(self, message):
        super().__init__(message)


class LucentDefaultRuleError(Exception):
    def __init__(self, message):
        super().__init__(message)


class LucentInconsistentFieldsError(Exception):
    def __init__(self, message):
        super().__init__(message)


class LucentParseError(Exception):
    def __init__(self, message):
        super().__init__(message)


class LucentFileNotFoundError(Exception):
    def __init__(self, message):
        super().__init__(message)
