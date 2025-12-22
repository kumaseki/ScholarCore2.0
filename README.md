# 安装依赖
``` python
pip install -r requirements.txt
```
# 配置.env.example
* DEEPSEEK_API_KEY可以在 https://platform.deepseek.com 获取。
* 我调整过prompt，token消耗不会太大，充5块就够用了，单日的爬取任务应该能控制在几分钱，5块能覆盖几个月需求。
* 需要使用邮件功能的需要配置IMAP或者POP3。
* 注意密码不是邮箱密码是授权码。

# daily_score
* daily_score是一个基于deepseek的论文评分工具，从arxiv上爬取论文，并根据用户设定的角色，阅读论文的标题、摘要，对论文多大程度符合用户的兴趣和口味进行评分。
* 评分范围是0-5分，0分表示完全不值得阅读，5分则表示完全符合用户的兴趣和口味。

# 配置settings.yaml
* 重点配置daily_news，daily_news包含以下5个部分：
  * subjects：爬取的arxiv论文类别，可以根据自己的需求修改，多个类别用逗号隔开。arxiv官方的分类页面：https://arxiv.org/archive/ 根据自己的学科和需要进行选择。
  * fields：设定大研究领域，例如网络安全、人工智能等（也可以稍微小一点）。
  * user_profile：输入deepseek的用户身份画像，根据实际情况修改。
  * white_list_keywords：核心关键词（白名单），命中白名单适当加分。
  * negative_patterns：负面关键词（黑名单），命中黑名单最大分数限制在3.5。

* 其余参数说明
* system：系统设置，最好保持默认。
  * log_level：日志等级，默认INFO。
  * data_root：数据根目录，默认./data。
* llm：llm调用设置。默认调用deepseek。
* 如果不使用deepseek，可能需要修改src/drivers/llm.py和src/services/daily_flow.py文件中的api调用部分代码。
  * model：模型名称。
  * base_url：模型API基础URL。
  * temperature：模型温度参数，默认0.2。
  * max_tokens：模型输出最大token数，默认8000。
* email：邮件发送设置，根据实际情况修改。
  * send_threshold：发送阈值，低于这个分数的根本不发邮件，默认3.5分。
  * top_k：根据评分排序后，每次发送的论文数量，默认30篇。

# 指令格式
``` python
example: python main.py daily --days 1 --force-email --limit 100
```
* --days: 向前爬取的天数，默认1天。
* --force-email: 是否在没有高分论文时也发送邮件，默认False。
* --limit: 每次爬取的论文数量限制，默认为3000。

# 日报邮件
高于settings.yaml中设定阈值评分的论文，会按照评分进行排序，根据用户在.env中预设的信息发送前top-k篇。
如果运行--force-email，不论是否存在高分论文，总会发送评分大于2.0的论文的前top-k篇。
邮件内容包含：
1. 高分论文列表，包括arxiv编号、论文标题、作者、摘要、链接等信息。
2. 对每个论文的打分结果，包括deepseek给出的分数和原因。
3. 高分论文会被下载，邮件中会提示。

# 输出和储存
所有下载的高分论文和经deepseek打分的结果会被保存到data目录下。
下载的高分论文会被存到data/inbox待阅读归档（或后续功能处理），命名包括arxiv编号和论文名称。
data/raw_cache提供了arxiv爬取结果的存档。
经deepseek打分后的结果会被存到data/reports下对应的年份/月份文件夹，并按日期归档。


