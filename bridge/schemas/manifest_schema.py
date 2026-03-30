"""Manifest schema used by bridge import/transcode pipeline."""

MANIFEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Bridge Audio Import Manifest",
    "type": "object",
    "required": ["id", "sourcePath", "sourceFormat", "analysis", "checksum", "original", "derivedFormats"],
    "properties": {
        "id": {"type": "string"},
        "sourcePath": {"type": "string"},
        "sourceFormat": {
            "type": "object",
            "properties": {
                "container": {"type": "string"},
                "sampleRateHz": {"type": "integer"},
                "channels": {"type": "integer"},
                "sampleWidthBytes": {"type": "integer"},
                "interleaved": {"type": "boolean"},
            },
            "required": ["container"],
            "additionalProperties": True,
        },
        "analysis": {
            "type": "object",
            "properties": {
                "integratedLUFS": {"type": ["number", "null"]},
                "truePeakDbfs": {"type": ["number", "null"]},
                "peakDbfs": {"type": ["number", "null"]},
            },
            "required": ["integratedLUFS", "truePeakDbfs", "peakDbfs"],
            "additionalProperties": False,
        },
        "checksum": {
            "type": "object",
            "properties": {
                "algorithm": {"const": "sha256"},
                "value": {"type": "string", "minLength": 64, "maxLength": 64},
            },
            "required": ["algorithm", "value"],
            "additionalProperties": False,
        },
        "original": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "lineage": {"type": "object"},
            },
            "required": ["path", "lineage"],
            "additionalProperties": True,
        },
        "derivedFormats": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["path", "format", "lineage", "checksum"],
                "properties": {
                    "path": {"type": "string"},
                    "format": {"type": "object"},
                    "analysis": {"$ref": "#/$defs/analysis"},
                    "checksum": {"$ref": "#/$defs/checksum"},
                    "lineage": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "source": {"type": "string"},
                            "method": {"type": "string"},
                            "normalization": {
                                "type": "object",
                                "properties": {
                                    "enabled": {"type": "boolean"},
                                    "targetIntegratedLUFS": {"type": "number"},
                                    "truePeakCeilingDbfs": {"type": "number"},
                                },
                                "additionalProperties": False,
                            },
                        },
                        "required": ["type"],
                        "additionalProperties": True,
                    },
                },
                "additionalProperties": True,
            },
        },
    },
    "$defs": {
        "analysis": {
            "type": "object",
            "properties": {
                "integratedLUFS": {"type": ["number", "null"]},
                "truePeakDbfs": {"type": ["number", "null"]},
                "peakDbfs": {"type": ["number", "null"]},
            },
            "required": ["integratedLUFS", "truePeakDbfs", "peakDbfs"],
        },
        "checksum": {
            "type": "object",
            "properties": {
                "algorithm": {"const": "sha256"},
                "value": {"type": "string", "minLength": 64, "maxLength": 64},
            },
            "required": ["algorithm", "value"],
        },
    },
    "additionalProperties": False,
}
