from fastapi import status


class SmartFitError(Exception):
    """Base exception for all domain-specific SmartFit failures."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "SMARTFIT_ERROR",
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class LandmarkDetectionError(SmartFitError):
    """Raised when body landmarks cannot be detected reliably."""

    def __init__(self, message: str = "Unable to detect body landmarks.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="LANDMARK_DETECTION_ERROR",
        )


class MeasurementConversionError(SmartFitError):
    """Raised when pixel-to-centimeter conversion cannot be computed."""

    def __init__(self, message: str = "Unable to convert measurements.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="MEASUREMENT_CONVERSION_ERROR",
        )


class TryOnGenerationError(SmartFitError):
    """Raised when virtual try-on rendering fails."""

    def __init__(self, message: str = "Unable to generate virtual try-on image.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="TRYON_GENERATION_ERROR",
        )
