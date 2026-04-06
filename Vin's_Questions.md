1. How could we handle 'agent got stuck' scenarios?
In this project agent got stuck scenarios automatically not handled.
But to mitigate that we can introduce some timeout logic, also we can implement readiness and liveness probe

2. Any automatic timeout/circuit breaker patterns coming out form this framework ?
Timeout can be added using model config spec, but it works only for kagent agents, if you have BYO agent you should implement it separately

3. How does kgateway handle model failover?
In this project there is no model failover, but it can be added by setting multiple models in priority list

4. Can we automatically switch from OpenAI to Claude to local model ?
Depends on what means automaticaly and in which context:
- For fallback purpose I already described how to do that, I belive we can create route to local model
- For balancing we also can configure multiple backends (which will be choosed by Power of Two)

In this project there is no automatic switch between all of those

5. Could we seamlessly handle the response formats form these providers?
For kagent agents no, it is poorly instrumented and requires some formating
For my agent it is better instrumented but still not great
So I have to look at something like semantic conversions

6. Can we version the agents built form kagent?
We can version BYO agents, but we can't version kagent's agents

7. Any blue/green or canary deployment patterns for agents?
Out of the box there is no support for deployment patterns for agents, but we can use argo or flux CRDs to control deployment of agents and utilize them using corresponding agents

8. What's the fastmcp-python framework mentioned?
Fastmcp is a Python framework for building MCP servers using a simple @mcp.tool() decorator, that's really easy to use

9. Is it the easiest path to mcp?
For building your own MCP with your own tools I believe yes

10. About finops: how much control I can have?
You can controll it on provider API level, on gateway level and on model config level. Also it is possible to set some limits in code but I would like not to do that

11. Token level / per agent level
We can set max tokens on agentBackend and maxTokens for model config

12. Can I implement custom cost controls?
Probably yes but it will require development of separate controller
Also it is possible to trace cost with phoenix

13. Per-agent budgets or depth of Token limits
We can create separate model config for each agent and set different limits there

14. vLLM suitable for agents with many back and forth tool calls, or is it better for single shot inference?
vLLM excels at throughput for single-shot or batch inference. For agents making 15+ sequential LLM calls (tool-calling loops), each call is a
separate request — vLLM's continuous batching helps if multiple agents are running concurrently, but adds latency per individual request vs. 
calling OpenAI directly. It's a trade-off: better for cost/throughput at scale, not necessarily better for single-agent latency.

15. llm-d's scheduler - helps when agents makes 15 llms calls?
Yes, meaningfully so. It can orchestrate to which vLLM send requests depending on load an KV cache 