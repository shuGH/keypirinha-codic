# Keypirinha launcher (keypirinha.com)

import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet
from collections import namedtuple
import json
import traceback
import urllib.error
import urllib.parse
import urllib.request

IS_DEBUG = True

class Codic(kp.Plugin):
    """
    One-line description of your plugin.

    This block is a longer and more detailed description of your plugin that may
    span on several lines, albeit not being required by the application.

    You may have several plugins defined in this module. It can be useful to
    logically separate the features of your package. All your plugin classes
    will be instantiated by Keypirinha as long as they are derived directly or
    indirectly from :py:class:`keypirinha.Plugin` (aliased ``kp.Plugin`` here).

    In case you want to have a base class for your plugins, you must prefix its
    name with an underscore (``_``) to indicate Keypirinha it is not meant to be
    instantiated directly.

    In rare cases, you may need an even more powerful way of telling Keypirinha
    what classes to instantiate: the ``__keypirinha_plugins__`` global variable
    may be declared in this module. It can be either an iterable of class
    objects derived from :py:class:`keypirinha.Plugin`; or, even more dynamic,
    it can be a callable that returns an iterable of class objects. Check out
    the ``StressTest`` example from the SDK for an example.

    Up to 100 plugins are supported per module.

    More detailed documentation at: http://keypirinha.com/api/plugin.html
    """

    # 項目の設定
    Section = namedtuple('Section', ('enabled', 'item_label', 'project_id', 'casing', 'acronym_style'))
    # クエリ
    Query = namedtuple('Query', ('text', 'project_id', 'casing', 'acronym_style'))
    # 結果（第一候補の結果）
    Result = namedtuple('Result', ('successful', 'text', 'translated'))
    # 単語別の候補
    Word = namedtuple('Word', ('successful', 'text', 'translated', 'candidates'))

    API_URL = "https://api.codic.jp/v1/engine/translate.json"
    BROWSE_URL = "https://codic.jp/engine?"

    API_CASING_DICT = {
        "camel": "camel",
        "pascal": "pascal",
        "lower underscore": "lower underscore",
        "upper underscore": "upper underscore",
        "hyphen": "hyphen"
    }
    API_ACRONYM_STYLE_DICT = {
        "ms naming guidelines": "MS naming guidelines",
        "camel strict": "camel strict",
        "literal": "literal"
    }

    # 翻訳表示レイヤー：入力を受け取りAPIを叩く
    ITEMCAT_TRANSLATE = kp.ItemCategory.USER_BASE + 1
    # 結果アクションレイヤー：結果に対しアクションを表示
    ITEMCAT_RESULT = kp.ItemCategory.USER_BASE + 2
    # 候補選択レイヤー：一つずつ候補を表示
    ITEMCAT_CANDIDATE = kp.ItemCategory.USER_BASE + 3

    ITEM_ARGS_SEP = ":"

    CONFIG_SECTION_DEFAULTS = "defaults"
    CONFIG_SECTION_CUSTOM_ITEM = "custom_item"

    ACTION_COPY_RESULT = "copy_result"
    ACTION_BROWSE = "browse"
    ACTION_BROWSE_PRIVATE = "browse_private"
    ACTION_COPY_URL = "copy_url"

    DEFAULT_SECTION = Section(True, "Codic:", "", "", "")
    DEFAULT_IDLE_TIME = 0.3
    ACCESS_TOKEN = ''

    # 現在の状態保持用（Section以外は非表示になった時に初期化される）
    _sections = []
    _query = None
    _result = None
    _words = {}

    def __init__(self):
        super().__init__()

    # 初期化時
    def on_start(self):
        self._sections = []
        self._query = None
        self._result = None
        self._words = {}

        self._read_config()

        # アクションを追加
        actions = [
            self.create_action(
                name=self.ACTION_COPY_RESULT,
                label="Copy result",
                short_desc="Copy result to clipboard"),
            self.create_action(
                name=self.ACTION_BROWSE,
                label="Open in browser",
                short_desc="Open your query in Codic"),
            self.create_action(
                name=self.ACTION_BROWSE_PRIVATE,
                label="Open in browser (Private Mode)",
                short_desc="Open your query in Codic (Private Mode)"),
            self.create_action(
                name=self.ACTION_COPY_URL,
                label="Copy URL",
                short_desc="Copy resulting URL to clipboard")
        ]
        self.set_actions(self.ITEMCAT_RESULT, actions)

    # カタログが生成された時
    def on_catalog(self):
        # 項目をカタログに追加する
        catalog = self._read_config()
        if catalog:
            self.set_catalog(catalog)

    # キー入力時
    def on_suggest(self, user_input, items_chain):
        if not items_chain:
            return

        current_item = items_chain[-1]

        if current_item.category() == self.ITEMCAT_TRANSLATE:
            self._on_suggest_translate(user_input, current_item)
        elif current_item.category() == self.ITEMCAT_RESULT:
            self._on_suggest_result(user_input, current_item)
        elif current_item.category() == self.ITEMCAT_CANDIDATE:
            self._on_suggest_translate(user_input, current_item)

    def _on_suggest_translate(self, user_input, current_item):
        suggestions = []

        query = self._extract_search_query(current_item, user_input)
        self._info(query)

        if len(query.text):
            if self.should_terminate(self.DEFAULT_IDLE_TIME):
                return

            result = self.Result(False, '', '')
            words = []

            try:
                self._query = query
                opener = kpnet.build_urllib_opener()
                req = self._build_api_request(query)

                with opener.open(req) as conn:
                    response = conn.read()
                if self.should_terminate():
                    return

                result, words = self._parse_api_response(response)
                self._info(result, words)

            except urllib.error.HTTPError as exc:
                suggestions.append(self.create_error_item(
                    label=user_input, short_desc=str(exc)))
            except Exception as exc:
                suggestions.append(self.create_error_item(
                    label=user_input, short_desc="Error: " + str(exc)))
                traceback.print_exc()

            suggestions = [self._create_result_item(query, result)]

        if suggestions:
            self.set_suggestions(suggestions, kp.Match.ANY, kp.Sort.NONE)

    def _on_suggest_result(self, user_input, current_item):
        pass

    def _on_suggest_candidate(self, user_input, current_item):
        pass

    # アイテム選択時
    def on_execute(self, item, action):
        if not action:
            return

        if item.category() == self.ITEMCAT_TRANSLATE:
            self._on_execute_translate(item, action)
        elif item.category() == self.ITEMCAT_RESULT:
            self._on_execute_result(item, action)
        elif item.category() == self.ITEMCAT_CANDIDATE:
            self._on_execute_candidate(item, action)

    def _on_execute_translate(self, item, action):
        pass

    def _on_execute_result(self, item, action):
        url = self._build_browse_url(self._query)
        name = action.name() if action else self.ACTION_COPY_RESULT

        if name == self.ACTION_COPY_RESULT:
            kpu.set_clipboard(item.label())
        elif name == self.ACTION_BROWSE:
            kpu.web_browser_command(private_mode=False, url=url, execute=True)
        elif name == self.ACTION_BROWSE_PRIVATE:
            kpu.web_browser_command(private_mode=True, url=url, execute=True)
        elif name == self.ACTION_COPY_URL:
            kpu.set_clipboard(url)

    def _on_execute_candidate(self, item, action):
        pass

    # LaunchBoxが表示された時
    def on_activated(self):
        pass

    # LaunchBoxが非表示になった時
    def on_deactivated(self):
        self._query = None
        self._result = None
        self._words = {}

    # 何かしらのイベント発生時
    def on_events(self, flags):
        # コンフィグ変更時
        if flags & (kp.Events.APPCONFIG | kp.Events.PACKCONFIG | kp.Events.NETOPTIONS):
            self._read_config()
            self.on_catalog()

    # コンフィグを読み込む
    def _read_config(self):
        def _warn_lang_code(name, section, fallback):
            fmt = (
                "Invalid {} value in [{}] config section. " +
                "Falling back to default: {}")
            self.warn(fmt.format(name, section, fallback))

        def _warn_skip_custitem(name, section):
            fmt = (
                "Invalid {} value in [{}] config section. " +
                "Skipping custom item.")
            self.warn(fmt.format(name, section))

        catalog = []
        settings = self.load_settings()

        self._info('load setting.')

        # [default_item]
        self.DEFAULT_SECTION = self._create_section(settings, self.CONFIG_SECTION_DEFAULTS, self.DEFAULT_SECTION.item_label)
        self.DEFAULT_IDLE_TIME = settings.get_float("idle_time", section=self.CONFIG_SECTION_DEFAULTS, fallback=self.DEFAULT_IDLE_TIME, min=0.25, max=3)
        self.ACCESS_TOKEN = self._load_accesstoken(settings)

        self._info(self.DEFAULT_SECTION, self.DEFAULT_IDLE_TIME, self.ACCESS_TOKEN)

        self._sections = []

        # 項目追加
        if self.DEFAULT_SECTION.enabled:
            self._sections.append(self.DEFAULT_SECTION)
            catalog.insert(0, self._create_translate_item(self.DEFAULT_SECTION, len(self._sections) - 1))

        # [custom_item/*]
        for section_label in settings.sections():
            if not section_label.lower().startswith(self.CONFIG_SECTION_CUSTOM_ITEM + "/"):
                continue

            section_name = section_label[len(self.CONFIG_SECTION_CUSTOM_ITEM) + 1:].strip()
            if not len(section_name):
                self.warn('Invalid section name: "{}". Skipping section.'.format(section_label))
                continue

            section = self._create_section(settings, section_label, section_name)
            self._sections.append(section)

            self._info(section)

            # 項目追加
            catalog.append(self._create_translate_item(section, len(self._sections) - 1))

        return catalog

    # 翻訳表示に遷移する項目を作成
    def _create_translate_item(self, section, index):
        # pascal, camel 時しか有効でないため無視する
        acronym_style = section.acronym_style if section.acronym_style else "default"
        acronym_style = acronym_style if (section.casing in {"pascal", "camel"}) else ""
        desc = "Codic Translate {}({}{}):".format(
            "[{}] ".format(section.project_id) if section.project_id else "",
            "{}".format(section.casing) if section.casing else "default",
            ", {}".format(acronym_style) if acronym_style else ""
        )

        self._info(section.item_label, index, str(index))

        return self.create_item(
            category=self.ITEMCAT_TRANSLATE,
            label=section.item_label,
            short_desc=desc,
            target=str(index),
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS)

    # 結果アクションに遷移する項目を作成
    def _create_result_item(self, query, result):
        # pascal, camel 時しか有効でないため無視する
        acronym_style = query.acronym_style if query.acronym_style else "default"
        acronym_style = acronym_style if (query.casing in {"pascal", "camel"}) else ""
        desc = "Codic Translate {}({}{}): {}".format(
            "[{}] ".format(query.project_id) if query.project_id else "",
            "{}".format(query.casing) if query.casing else "default",
            ", {}".format(acronym_style) if acronym_style else "",
            query.text if query.text else ""
        )
        target = query.project_id + self.ITEM_ARGS_SEP + query.casing + self.ITEM_ARGS_SEP + query.acronym_style

        item = self.create_item(
            category=self.ITEMCAT_RESULT,
            label=result.translated,
            short_desc=desc,
            target=target,
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.IGNORE)

        bag = desc.replace("Codic Translate ", "")
        item.set_data_bag(bag)

        return item

    # @TODO: 候補選択に遷移する項目を作成
    def _create_candidate_item(self, query, word):
        label = word.translated + ' + ?'
        short_desc = ""
        item = self.create_item(
            category=self.ITEMCAT_TRANSLATE,
            label=label,
            short_desc=short_desc,
            target=label,
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.IGNORE)

        return item

    # 項目の設定を作成
    def _create_section(self, settings, section_label, section_name):
        casing = settings.get_stripped("casing", section=section_label, fallback=self.DEFAULT_SECTION.casing).lower()
        casing = casing if casing in self.API_CASING_DICT.keys() else ""
        acronym_style = settings.get_stripped("acronym_style", section=section_label, fallback=self.DEFAULT_SECTION.acronym_style).lower()
        acronym_style = acronym_style if acronym_style in self.API_ACRONYM_STYLE_DICT.keys() else ""

        return self.Section(
            settings.get_bool("enable", section=section_label, fallback=self.DEFAULT_SECTION.enabled),
            settings.get_stripped("item_label", section=section_label, fallback=section_name),
            settings.get_stripped("project_id", section=section_label, fallback=self.DEFAULT_SECTION.project_id),
            casing,
            acronym_style
        )

    # 入力からクエリを作成
    def _extract_search_query(self, item, user_input):
        self._info(item.label(), item.target())
        index = int(item.target())
        if len(self._sections) <= index:
            return None

        section = self._sections[index]
        text = user_input.strip() if user_input else ''

        return self.Query(text, section.project_id, section.casing, section.acronym_style)

    # レスポンスから結果と単語別の候補を作成
    def _parse_api_response(self, response):
        response = response.decode(encoding="utf-8", errors="strict")
        response = response.replace(",,", ",null,").replace("[,", "[null,")

        data = json.loads(response)[0]
        result = self.Result(
            data['successful'],
            data['text'],
            data['translated_text']
        )

        words = []
        for word in data['words']:
            words.append(self.Word(
                word['successful'],
                word['text'],
                word['translated_text'],
                [candidate['text'] for candidate in word['candidates']]
            ))

        return result, words

    # APIアクセス用のURLを作成する
    def _build_api_request(self, query):
        data = {
            'text': query.text
        }
        if query.project_id:
            data['project_id'] = query.project_id
        if query.casing in self.API_CASING_DICT.keys():
            data['casing'] = self.API_CASING_DICT[query.casing]
        if query.acronym_style in self.API_ACRONYM_STYLE_DICT.keys():
            data['acronym_style'] = self.API_ACRONYM_STYLE_DICT[query.acronym_style]
        headers = {
            'Authorization': 'Bearer {}'.format(self.ACCESS_TOKEN),
            'Content-Type': 'application/json'
        }

        self._info(data, headers)

        return urllib.request.Request(self.API_URL, json.dumps(data).encode(), headers)

    # Webブラウズ用のURLを作成する
    def _build_browse_url(self, query):
        data = {
            'text': query.text
        }
        if query.project_id:
            data['project_id'] = query.project_id
        if query.casing in self.API_CASING_DICT.keys():
            data['casing'] = self.API_CASING_DICT[query.casing]
        if query.acronym_style in self.API_ACRONYM_STYLE_DICT.keys():
            data['acronym_style'] = self.API_ACRONYM_STYLE_DICT[query.acronym_style]

        return self.BROWSE_URL + urllib.parse.urlencode(data)

    # アクセストークンを取得する
    def _load_accesstoken(self, settings):
        # 設定から取得
        if not IS_DEBUG:
            return settings.get_stripped("access_token", section=self.CONFIG_SECTION_DEFAULTS, fallback="")

        # デバッグ用：ローカルファイルから取得
        try:
            lines = self.load_text_resource("ACCESS_TOKEN").splitlines()
        except Exception as exc:
            self.warn("Failed to load AccessToken. Error: {}".format(exc))

        return lines[0] if lines[0] else ''

    # デバッグ用：ログ出力
    def _info(self, *args):
        if IS_DEBUG:
            if len(args) == 1:
                self.info(args[0])
            else:
                self.info(args)
        return
