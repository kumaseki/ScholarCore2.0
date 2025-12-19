# 安装依赖
pip install -r requirements.txt
# 配置.env.example
DEEPSEEK_API_KEY可以在 https://platform.deepseek.com 获取。
我调整过prompt，token消耗不会太大，充5块就够用了，单日的爬取任务应该能控制在几分钱，5块能覆盖几个月需求。
需要使用邮件功能的需要配置IMAP或者POP3。
注意密码不是邮箱密码是授权码。
# 配置settings.yaml
重点配置daily_news部分和rubric部分。
daily_news包含subjects和user_profile两个部分。
subjects是爬取的arxiv论文类别，可以根据自己的需求修改，多个类别用逗号隔开。
arxiv官方的分类页面：https://arxiv.org/archive/ 根据需要自己选择。
user_profile是输入deepseek的用户身份prompt，我给出了一个范例，根据实际情况自己修改。
接下来重点说下rubric部分。这部分是论文日报功能的核心，用户需要根据自己的兴趣设计rubric。
rubric被设计为一类Few-shot prompt，重点关注一篇论文对用户的效用（也就是多大可能用户会感兴趣并阅读）。
用户需要给出不同分数的论文案例，从而引导deepseek给出符合自己taste的打分。
一条rubric包含标题、描述和得分三个部分。
给出rubric的重点在于描述部分，说明白为何得这个分数。一个好的rubric应该用简短准确的语言解释清楚。
另一个需要注意的是，对于同一个分数，可能存在不同类型的论文，因此对于同一得分给出的rubric应尽可能覆盖所有可能的类别，同时保证不同类别、不同分数之间的区分度。
# 指令格式
```
example: python main.py daily --days 1 --force-email --limit 100
```
--days: 向前爬取的天数，默认1天。
--force-email: 是否发送邮件，默认False。
--limit: 每次爬取的论文数量限制，默认为3000。
# 日报邮件
如果运行--force-email，所有符合rubric的、高于settings.yaml中设定阈值评分的以及设定的top-k篇高分论文会被打包成一个邮件，根据用户在.env中预设的信息进行发送。
邮件内容包含：
1. 符合rubric的高分论文列表，包括arxiv编号、论文标题、作者、摘要、链接等信息。
2. 对每个论文的打分结果，包括deepseek给出的分数和原因。
3. 高分论文会被下载，邮件中会提示。
# 输出和储存
所有下载的高分论文和经deepseek打分的结果会被保存到data目录下。
下载的高分论文会被存到data/inbox待阅读归档（或后续功能处理），命名包括arxiv编号和论文名称。
data/raw_cache提供了arxiv爬取结果的存档。
经deepseek打分后的结果会被存到data/reports下对应的年份/月份文件夹，并按日期归档。


