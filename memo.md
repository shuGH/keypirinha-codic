# 開発メモ

## ■ Codic仕様調査

公式：[API | codic](https://codic.jp/docs/api)

### デバッグ

* AをBに置き換えるがおかしい

### APIとクエリ

* 翻訳だけならエンジンAPIしか使用しないで大丈夫
* アクセストークンをリクエストヘッダーに含める必要がある

GET|POST https://api.codic.jp/v1/engine/translate.json
Authorization: Bearer YOUR_ACCESS_TOKEN

|           Name           | タイプ |                                             Description                                              |
| ------------------------ | ------ | ---------------------------------------------------------------------------------------------------- |
| text                     | string | 変換する文字列（日本語）を設定します。                                                               |
|                          |        | 文字列を改行（LF)で区切ることで、一度にまとめて変換することもできます（最大3件まで）。               |
| project_id [optional]    | string | 変換で使用するプロジェクト（辞書）のidを指定します。                                                 |
|                          |        | これは、自分がアクセス可能なプロジェクトである必要があります。                                       |
|                          |        | アクセス可能なプロジェクトのidを取得するには、プロジェクト一覧を使用します。                         |
|                          |        | 指定がない場合は、システム辞書が使われます。                                                         |
| casing [optional]        | string | camel, pascal, lower underscore, upper underscore, hyphenのいずれかを指定します。                    |
|                          |        | デフォルトは、ケースの変換は行いません（登録された単語のスペース区切りになります）。                 |
| acronym_style [optional] | string | パラメータcasingに、camel, pascalのいずれかを指定した場合の頭字語（例: SOA）の処理方法を指定します。 |
|                          |        | MS naming guidelines, camel strict, literalのいずれかを指定します。                                  |

#### ケース

* camel：camelCase
* pascal：PascalCase
* lower underscore：lower_underscore
* upper underscore：UPPER_UNDERSCORE
* hyphen：hyphen-case

参考：https://codic.jp/docs/guide/naming

#### 頭字語（acronym）

PascalCase / camelCaseの時のみ

* MS naming guidelines：2文字まではすべて大文字、3文字以上は先頭だけ大文字、camelCaseの最初の単語はすべて小文字
* camel strict：先頭だけ大文字、camelCaseの最初の単語はすべて小文字
* literal：登録単語に準じる、camelCaseの最初の単語はすべて小文字

### リクエスト例

```
POST https://api.codic.jp/v1/engine/translate.json HTTP/1.1
Authorization: Bearer YOUR_ACCESS_TOKEN
content-type: application/json

{
    "text": "本当に存在するか"
}
```

```
GET https://api.codic.jp/v1/engine/translate.json?project_id=123&text=こんにちわ世界&casing=lower+underscore
```

### レスポンス例

```
[
  {
    "successful": false,  // 翻訳が成功したかどうか
    "text": "こんにちわ世界"
    "translated_text": "hello_世界",
    "words": [
      {
        "successful": true,
        "text": "こんにちわ",
        "translated_text": "hello",
        "candidates": [
          {
            "text": "hello"
          },
          {
            "text": "hi"
          }
        ]
      },
      {
        "successful": false,
        "text": "世界",
        "translated_text": null,
        "candidates": []
      }
    ]
  }
]
```

```
{
  "errors":[
    {
      "code": 404,
      "message": "ページが存在しません。",
      "context": null
    }
  ]
}
```

## ■ Keypirinhaについて

### カスタムコマンド例

```
[custom_item/TranslateToEnglish]
enable = yes
item_label = ToEn:
input_lang = auto
output_lang = en
```
