# 必要なライブラリをインポート
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from mcp.client.stdio import stdio_client, StdioServerParameters

# AgentCoreランタイム用のAPIサーバーを作成
app = BedrockAgentCoreApp()

# エージェント呼び出し関数を、APIサーバーのエントリーポイントに設定
@app.entrypoint
async def invoke_agent(payload, context):

    # フロントエンドで入力されたプロンプトとAPIキーを取得
    prompt = payload.get("prompt")
    tavily_api_key = payload.get("tavily_api_key")

    ### この中が通常のStrandsのコード ----------------------------------
    # Tavily MCPサーバーを設定
    tavily_mcp_client = MCPClient(lambda: streamablehttp_client(
        f"https://mcp.tavily.com/mcp/?tavilyApiKey={tavily_api_key}"
    ))

    ###### 問題1: time mcp server をエージェントから利用できる様に定義しましょう ######
    time_mcp_client = MCPClient(lambda: stdio_client(
        StdioServerParameters(
            command="uvx",
            args=["mcp-server-time"]
        )
    ))

    ###### 問題1: ここまで ######

    ###### 問題2: エージェントが TavilyでのWeb検索の前に、必ず日付を確認するようにしましょう ######
    # MCPクライアントを起動したまま、エージェントを呼び出し
    with tavily_mcp_client, time_mcp_client:
        tools = tavily_mcp_client.list_tools_sync() + time_mcp_client.list_tools_sync()
        
        agent = Agent(
            model = "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            tools = tools,
            system_prompt="""2つのツールを使って日本語で応対して。
            1. tavily mcp：Tavily API を利用しWeb検索できます。実行の前には time mcp を利用します。
            2. time mcp：現在時刻を取得できます。
            語尾は「〜だゾ。」にしてください。
            """
        )

	###### 問題2: ここまで ######

        # エージェントの応答をストリーミングで取得
        stream = agent.stream_async(prompt)
        async for event in stream:
            yield event
    ### ------------------------------------------------------------

# APIサーバーを起動
if __name__ == "__main__":
    app.run()
