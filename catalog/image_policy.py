"""Brand image loading policies for the v2 catalog UI."""

TOPSPEED_UPLOAD_PREFIX = "https://topspeed.tsm-models.com/upload/"
INNO_UPLOAD_PREFIX = "https://www.inno-models.com/wp-content/uploads/"


IMAGE_POLICIES = {
    "mini-gt": {"maxImages": None},
    "ar": {"maxImages": None},
    "topspeed": {
        "maxImages": 4,
        "card": {
            "proxy": "/api/topspeed-thumb",
            "sourcePrefix": TOPSPEED_UPLOAD_PREFIX,
        },
        "modal": {
            "proxy": "/api/topspeed-thumb",
            "sourcePrefix": TOPSPEED_UPLOAD_PREFIX,
        },
    },
    "spark": {"maxImages": 3},
    "spark64": {"maxImages": 3},
    "inno": {
        "maxImages": 3,
        "card": {
            "proxy": "/api/inno-image",
            "sourcePrefix": INNO_UPLOAD_PREFIX,
        },
        "modal": {
            "proxy": "/api/inno-image",
            "sourcePrefix": INNO_UPLOAD_PREFIX,
        },
    },
    "poprace": {"maxImages": 4},
}


def image_policy_response():
    return IMAGE_POLICIES
