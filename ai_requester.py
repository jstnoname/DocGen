from parser import Position, PosWithBody
from typing import NamedTuple

from requests import post

SYS_INSTRUCTION = (
    "Ты помощник по программированию. Я буду давай тебе часть кода, а твоя задача проанализировать "
    "данный код и написать краткую документацию. Код может содержать только классы, функции или методы. "
    "Пиши документацию только с использованием символов ASCII, по следующему принципу: если это класс, "
    "то напиши краткое объяснения что данный класс делает, если это функции или метод, то пиши что "
    "данный код делает, после если есть аргументы, то для каждого аргумента на новой строке опиши что "
    "этот аргумент делает в виде 'имя аргумента':'зачем он нужен' и в конце, если метод или функция "
    "что-то возвращает, то так же на новой строке напиши 'return':'что возвращает данный код', если "
    "ничего не возвращается, то оставь 'return' пустым, то есть 'return':''."
    "Так же уточнения для написания документации: если ты пишешь документацию для класса, то пиши "
    "название этого класса, после через двоеточие описания класса. Если это метод или функция внутри "
    "класса, то пиши 'имя этого класса'/'имя этой функции или метода': описание. "
    "Описание аргументов пиши следующим образом: "
    "'имя этого класса'/'имя этой функции или метода'/'param имя аргумента':'описание аргумента'. "
    "Параметр 'return' так же указывай через 'имя этого класса'/'имя этой функции или метода' к чему "
    "относиться, то есть должно получиться 'имя этого класса'/'имя этой функции или метода'/'return'. "
    "Каждое описание пиши на новой строке, не допускай пустых строк. Сам код писать не нужно, пиши "
    "только документацию и строго следуй инструкциям. Если у объекта уже есть документация, то "
    "пропускай, такие методы, функции или классы менять не нужно. Пиши документацию только на английском языке"
)


class PosWithDoc(NamedTuple):
    Position: Position
    Documentation: str


class AIRequester:
    """
    AI Requester. Do requests to artificial intelligence and return documentation
    At this moment will do requests only to Gemini
    """

    def __init__(
        self,
        objects_to_doc: dict[str, PosWithBody],
        url: str = "https://weathered-truth-4ce8.alexspirin.workers.dev/v1/models/",
        model: str = "gemini-2.5-flash",
        apikey: str = "",
    ):
        """
        Init AIRequester.
        :param objects_to_doc: dict got from Parser
        """
        with open(".env", "r") as env:  # пока что будет так
            apikey = env.readlines()[1].strip().split('=')[1]

        self._url = f"{url}{model}:generateContent?key={apikey}"
        self._objects_to_doc = objects_to_doc
        self._body = {
            "contents": [
                {"role": "user", "parts": {"text": SYS_INSTRUCTION}},
                {"role": "user", "parts": [{"text": body} for body in self._get_outer_objects_to_doc()]},
            ]
        }

    def get_docs(self) -> dict[str, PosWithDoc]:
        return self._get_request_to_ai()

    def _get_request_to_ai(self) -> dict[str, PosWithDoc]:
        is_data_valid = False
        docs: dict[str, PosWithDoc] = {}

        while not is_data_valid:
            response = post(self._url, json=self._body, headers={"Content-Type": "application/json"})

            if response.status_code != 200:
                continue

            documentations: str = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            validated_docs = self._validate_data(documentations)
            if not validated_docs:
                continue

            for key, value in validated_docs.items():
                docs[key] = PosWithDoc(Position=self._objects_to_doc[key].position, Documentation=value)
            is_data_valid = True

        return docs

    def _validate_data(self, documentations: str) -> dict[str, str] | None:
        """
        validate documentations to check correctness
        :param documentations: doc from AI
        :return: None if data not valid, dict of object as key and doc this object as value
        """
        result: dict[str, str] = {}

        for doc in documentations.split("\n"):
            if doc.strip() == "":
                return None
            object_name, object_doc = doc.split(":", 1)

            for key in self._objects_to_doc.keys():
                if key.endswith(object_name):
                    result[key] = object_doc.strip()
                    break
                elif key.endswith(object_name[: ((arg_index := object_name.rfind('/') + 1) - 1)]) and (
                    object_name[arg_index:].startswith("param") or object_name[arg_index:].startswith("return")
                ):
                    result[key] += '\n:' + object_name[arg_index:] + ': ' + object_doc.strip()
                    break
            else:
                return None
        return result

    def _get_outer_objects_to_doc(self) -> list[str]:
        """
        get outer objects to doc to don't write double documentation
        :return: list of objects to doc
        """
        values = [value for _, value in self._objects_to_doc.items()]
        outer_objects: list[str] = ['\n'.join(values[0].body)]

        for i in range(len(self._objects_to_doc.values()) - 1):
            if values[i].position.end_line < values[i + 1].position.start_line:
                outer_objects.append('\n'.join(values[i + 1].body))

        return outer_objects
