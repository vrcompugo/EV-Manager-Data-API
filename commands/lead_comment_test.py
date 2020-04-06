import json

from app.modules.importer.sources.bitrix24._connector import post, get


def lead_comment_test():
    print(json.dumps(post("crm.timeline.comment.list", post_data={
        "filter[ENTITY_ID]": 4840,
        "filter[ENTITY_TYPE]": "lead"
    }), indent=2))
