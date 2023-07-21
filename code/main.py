import os
import threading
import time
import requests
import json
import urllib.parse
from queue import Queue


class MySpider:
    def __init__(self):
        self.project_dir = os.path.abspath("../")
        self.resource_dir = os.path.join(self.project_dir, "resources")
        self.proxies = {
            "http": "http://127.0.0.1:7890",
            "https": "https://127.0.0.1:7890"
        }
        self.base_prompt_url = "https://flowgpt.com/api/trpc/prompt.getPrompts"
        self.base_comment_url = "https://flowgpt.com/api/trpc/comment.getComments,user.getUserProfile"
        self.sort_mode = "top"
        self.prompt_queue = Queue()
        self.prompt_dataset = []
        self.download_thread_num = 200
        self.count = 0

    def get_prompt_by_page(self, page_id):
        # sort_mode = "top"
        tag_name = None
        query_name = None
        # 当 检索tag为None时，sort_mode不能为None。
        if not tag_name:
            inner_data = {"0": {
                "json": {"skip": 36 * (page_id - 1), "tag": None, "sort": self.sort_mode, "q": query_name,
                         "language": "en"},
                "meta": {"values": {"tag": ["undefined"], "q": ["undefined"]}}
            }}
        else:
            inner_data = {"0": {
                "json": {"skip": 36 * (page_id - 1), "tag": tag_name, "sort": self.sort_mode, "q": query_name,
                         "language": "en"},
                "meta": {"values": {"sort": ["undefined"], "q": ["undefined"]}}
            }}
        res_params = {
            "batch": 1,
            "input": json.dumps(inner_data, ensure_ascii=False)
        }
        try:
            res = requests.get(self.base_prompt_url, params=res_params, proxies=self.proxies)
        except requests.RequestException as error:
            print(error)
            time.sleep(5)
            res = requests.get(self.base_prompt_url, params=res_params, proxies=self.proxies)
        try:
            data_json = res.json()[0]["result"]["data"]["json"]
        except IndexError or KeyError as error:
            print(error)
            data_json = []
        prompt_list = []
        for each in data_json:
            prompt_id = each["id"]
            title = each["title"]
            uses = each["uses"]
            upvotes = each["upvotes"]
            popularity = each["popularity"]
            views = each["views"]
            ranking = each["ranking"]
            description = each["description"]
            initPrompt = each["initPrompt"]
            comment_count = each["comments"]

            prompt_list.append({
                "prompt_id": prompt_id,
                "title": title,
                "uses": uses,
                "upvotes": upvotes,
                "popularity": popularity,
                "views": views,
                "ranking": ranking,
                "description": description,
                "initPrompt": initPrompt,
                "comment_count": comment_count
            })
        return prompt_list

    def get_comment_by_prompt_id(self, prompt_id):
        inner_data = {"0": {"json": prompt_id}}
        res_params = {
            "batch": 1,
            "input": json.dumps(inner_data, ensure_ascii=False)
        }
        try:
            res = requests.get(self.base_comment_url, params=res_params, proxies=self.proxies)
        except requests.RequestException as error:
            print("Exception Occur:", error)
            time.sleep(5)
            res = requests.get(self.base_comment_url, params=res_params, proxies=self.proxies)
        try:
            result = res.json()[0]["result"]["data"]["json"]
        except IndexError as error:
            print("Index Error")
            result = []
        except KeyError as error:
            print("Key Error, The result don't fit the format")
            result = []
        comments = []
        for each in result:
            comments.append({
                "comment_id": each["id"],
                "created_time": each["createdAt"],
                "updated_time": each["updatedAt"],
                "content": each["body"]
            })
        return comments

    def generator(self):
        page = 1
        while True:

            temp_result = self.get_prompt_by_page(page)
            for each_prompt in temp_result:
                self.prompt_queue.put(each_prompt)
            if len(temp_result) < 36:
                break
            page += 1
        for i in range(self.download_thread_num):
            self.prompt_queue.put(None)

    def consumer(self):
        while True:
            each_prompt = self.prompt_queue.get()
            if each_prompt is None:
                break
            prompt_id = each_prompt["prompt_id"]

            comment_data = self.get_comment_by_prompt_id(prompt_id)
            each_prompt["comment"] = comment_data
            self.prompt_dataset.append(each_prompt)
            self.count += 1
            print(self.count, prompt_id, "\n")

    def run(self):
        generator_thread = threading.Thread(target=self.generator, args=())
        generator_thread.start()

        consumer_threads = []
        for i in range(self.download_thread_num):
            consumer_thread = threading.Thread(target=self.consumer, args=())
            consumer_thread.start()
            consumer_threads.append(consumer_thread)
        generator_thread.join()
        for consumer_thread in consumer_threads:
            consumer_thread.join()
        print("All thread down")
        print("Writing to file...")
        with open(os.path.join(self.resource_dir, "result.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(self.prompt_dataset, ensure_ascii=False))
        print("Writing Down")


if __name__ == "__main__":
    spider = MySpider()
    spider.run()

