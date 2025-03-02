from openai import OpenAI

def call_dify_app(user_message):
    """调用 Dify 应用的函数"""
    try:
        client = OpenAI(
            base_url="https://31904gabboieo2a7.ai-plugin.io/chat/completions",
            api_key="app-O8kvcpngDNbJLuAWfhldQMm0",
        )

        response = client.chat.completions.create(
            model="v1",
            messages=[{"role": "user", "content": user_message}],
            stream=True,
        )

        return response.choices[0].message.content
    except Exception as e:
        return f"调用 Dify 应用出错: {e}"


if __name__ == "__main__":
    user_input = "新增dify代理工具"
    app_response = call_dify_app(user_input)
    print(f"用户输入: {user_input}")
    print(f"Dify 应用回复: {app_response}")
