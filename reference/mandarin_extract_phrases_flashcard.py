from html.parser import HTMLParser
import json, re

class PhraseExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lessons = []
        self.current_lesson = None
        self.current_section = None
        self.current_phrase = None
        self.capture = None
        self.text_buf = ""
        self.in_phrase = False
        self.class_stack = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")

        if tag == "h2" and attrs_dict.get("id", "").startswith("lesson-"):
            self.capture = "lesson_title"
            self.text_buf = ""
        elif tag == "h3":
            self.capture = "section_title"
            self.text_buf = ""
        elif cls == "phrase":
            self.in_phrase = True
            self.current_phrase = {"trad": "", "pinyin": "", "meaning": ""}
        elif self.in_phrase:
            if cls == "trad":
                self.capture = "trad"
                self.text_buf = ""
            elif cls == "pinyin":
                self.capture = "pinyin"
                self.text_buf = ""
            elif cls == "meaning":
                self.capture = "meaning"
                self.text_buf = ""

    def handle_endtag(self, tag):
        if self.capture == "lesson_title" and tag == "h2":
            title = self.text_buf.strip()
            self.current_lesson = {"title": title, "sections": []}
            self.lessons.append(self.current_lesson)
            self.current_section = None
            self.capture = None
        elif self.capture == "section_title" and tag == "h3":
            title = self.text_buf.strip()
            if self.current_lesson is not None:
                self.current_section = {"title": title, "phrases": []}
                self.current_lesson["sections"].append(self.current_section)
            self.capture = None
        elif self.in_phrase and tag == "div":
            if self.capture == "trad":
                self.current_phrase["trad"] = self.text_buf.strip()
                self.capture = None
            elif self.capture == "pinyin":
                self.current_phrase["pinyin"] = self.text_buf.strip()
                self.capture = None
            elif self.capture == "meaning":
                self.current_phrase["meaning"] = self.text_buf.strip()
                self.capture = None
                # phrase complete, add to current section
                if self.current_section and self.current_phrase["trad"]:
                    self.current_section["phrases"].append(dict(self.current_phrase))
                elif self.current_lesson and self.current_phrase["trad"]:
                    # no section yet, create default
                    if not self.current_lesson["sections"]:
                        self.current_section = {"title": "Phrases", "phrases": []}
                        self.current_lesson["sections"].append(self.current_section)
                    self.current_lesson["sections"][-1]["phrases"].append(dict(self.current_phrase))
                self.in_phrase = False

    def handle_data(self, data):
        if self.capture:
            self.text_buf += data

with open("/tmp/mandarin-in-14-days.html", "r") as f:
    html = f.read()

ext = PhraseExtractor()
ext.feed(html)

# Filter out lessons with no phrases and sections with no phrases
for lesson in ext.lessons:
    lesson["sections"] = [s for s in lesson["sections"] if s["phrases"]]

ext.lessons = [l for l in ext.lessons if l["sections"]]

total = sum(len(s["phrases"]) for l in ext.lessons for s in l["sections"])
print(f"Extracted {len(ext.lessons)} lessons, {total} phrases total")
for l in ext.lessons:
    count = sum(len(s["phrases"]) for s in l["sections"])
    print(f"  {l['title']}: {count} phrases in {len(l['sections'])} sections")

with open("/tmp/phrases.json", "w") as f:
    json.dump(ext.lessons, f, ensure_ascii=False, indent=2)
