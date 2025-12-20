import sys

from docgen.records import BaseAIRequester, PosWithBody, PosWithDoc
from requests import post


class AIRequester(BaseAIRequester):
    def __init__(
        self,
        objects_to_doc: dict[str, PosWithBody],
        url: str = "https://weathered-truth-4ce8.alexspirin.workers.dev/v1/models/",
        model: str = "gemini-2.5-flash",
        apikey: str = "",
    ):
        super().__init__(objects_to_doc, url, model, apikey)

        self._full_url_to_ai: str = f"{url}{model}:generateContent?key={apikey}"

    def _validate_docs(self, docs: str | None) -> dict[str, PosWithDoc] | None:
        if docs is None:
            return None

        result: dict[str, PosWithDoc] = {}
        paths = sorted(list(self._objects_to_doc.keys()), key=list(self._objects_to_doc.keys()).index)

        for doc in docs.split("\n"):
            if doc.strip() == "" or ":" not in doc:
                continue

            object_name, object_doc = map(str.strip, doc.split(":", 1))

            for object_path in paths:
                if object_path.endswith(object_name):
                    result[object_path] = PosWithDoc(self._objects_to_doc[object_path].position, object_doc)
                    break
                elif "param" in object_name or "return" in object_name:
                    true_object_name, argument = object_name.rsplit('/', 1)

                    if object_path.endswith(true_object_name):
                        pos = result[object_path].Position
                        doc = result[object_path].Documentation + f"\n:{argument}: {object_doc}"
                        result[object_path] = PosWithDoc(pos, doc)
                        break

        return result if len(result.keys()) == len(paths) else None

    def _get_docs_from_ai(self) -> str | None:
        response = post(self._full_url_to_ai, json=self._body, headers={"Content-Type": "application/json"})

        if response.status_code == 429:
            print(f"To many requests. Please retry again after {response.json()["error"]["details"][-1]["retryDelay"]}")
            sys.exit(-1)

        return response.json()["candidates"][0]["content"]["parts"][0]["text"] if response.status_code == 200 else None
