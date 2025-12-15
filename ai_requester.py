from abc import ABC, abstractmethod
from parser import Position, PosWithBody
from typing import NamedTuple

from requests import RequestException, post

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
    "только документацию и строго следуй инструкциям. Пиши документацию только на английском языке"
)


class PosWithDoc(NamedTuple):
    Position: Position
    Documentation: str


class BaseAIRequester(ABC):
    """
    Base class for AIRequester. Inherit this class to create new requester to AI
    """

    def __init__(self, objects_to_doc: dict[str, PosWithBody], url: str, model: str, apikey: str):
        """
        Initialize BaseAIRequester.
        :param objects_to_doc:
        :param url:
        :param model:
        :param apikey:
        """
        self._url_to_ai = url
        self._api_key_to_ai = apikey
        self._model_of_ai = model

        self._objects_to_doc = objects_to_doc
        self._body = {
            "contents": [
                {"role": "user", "parts": {"text": SYS_INSTRUCTION}},
                {"role": "user", "parts": [{"text": body} for body in self._get_outer_objects_to_doc()]},
            ]
        }

    def _get_outer_objects_to_doc(self) -> list[str]:
        """
        get outer objects to doc to don't write double documentation
        :return: list of objects to doc
        """
        outer_objects: list[str] = []
        previous_key: str = ""

        for key, value in self._objects_to_doc.items():
            if previous_key == "":
                outer_objects.append(''.join(value.body))
                previous_key = key
            elif not key.startswith(previous_key):
                outer_objects.append(''.join(value.body))
                previous_key = key

        return outer_objects

    def get_docs(self) -> dict[str, PosWithDoc]:
        """
        Get documentation for AIRequester
        :return: dict, where key object to doc, value is doc
        """
        documentation: dict[str, PosWithDoc] = {}
        count_of_tries = 0

        while not documentation or count_of_tries < 3:
            docs = self._get_docs_from_ai()
            valid_docs = self._validate_docs(docs)
            count_of_tries += 1

            if valid_docs is not None:
                documentation = valid_docs

        if not documentation:
            raise RequestException("Cannot get documentation. Please try again")

        return documentation

    @abstractmethod
    def _get_docs_from_ai(self) -> str | None:
        """
        Get docs from AI
        :return: str of docs or None if you couldn't get docs
        """
        pass

    @abstractmethod
    def _validate_docs(self, docs: str | None) -> dict[str, PosWithDoc] | None:
        """
        validate documentation for AIRequester
        :param docs: docs from AI
        :return: dict, where key object to doc, value is doc if docs is valid else None
        """
        pass


class AIRequester(BaseAIRequester):
    def __init__(
        self,
        objects_to_doc: dict[str, PosWithBody],
        url: str = "https://weathered-truth-4ce8.alexspirin.workers.dev/v1/models/",
        model: str = "gemini-2.5-flash",
        apikey: str = "",
    ):
        with open(".env", "r") as env:  # пока что будет так
            apikey = env.readline().split('=')[1]

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
            raise RequestException(
                f"To many requests. Please retry again after {response.json()["error"]["details"][-1]["retryDelay"]}"
            )

        return response.json()["candidates"][0]["content"]["parts"][0]["text"] if response.status_code == 200 else None
