"""Public exception types for invalid inputs and unsupported computations."""


class LandscapeMetricsError(Exception):
    """Base exception for this package."""


class InvalidRasterError(LandscapeMetricsError):
    """Raised when raster values are not a supported categorical grid."""


class SpatialMetadataError(LandscapeMetricsError):
    """Raised when spatial units or affine metadata are insufficient."""


class ConfigurationError(LandscapeMetricsError):
    """Raised when a requested run configuration is unsupported."""


class TemporaryStorageError(LandscapeMetricsError):
    """Raised when out-of-core computation cannot safely use temporary storage."""


class UnsupportedMetricError(LandscapeMetricsError):
    """Raised when a requested metric is outside the supported v0.1 set."""
