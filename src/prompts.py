import jinja2

def render_prompt(template: str, **kwargs):
    tpl = jinja2.Template(template)
    return tpl.render(**kwargs)

topic_change_prompt = """
You are a therapist assistant. You read a running window of a streamed therapy transcript. 
Your goal is to identify changes in topic and flag that to the therapist.
If the discussion covers a topic that is similar to an existing topic, you should use the existing topic.

You are given: 
- a list of previously discussed topics 
- the topic that was most recently discussed 
- a summary of the discussion of this topic 
- the full transcript of the next portion of the conversation.

You output (YAML format): 
topic: the current topic being discussed, in three words or less
summary: if the topic has changed, a summary of the conversation so far

Topic List: 
{{topics}}
Most Recent Topic: 
{{topic}}
Most Recent Topic Summary: 
{{summary}}
Current Transcript:
{{transcript}}
Output: 
"""

entity_extraction_prompt = """
You are a therapist assistant. You read a running window of a streamed therapy transcript. 
Your goal is to pay attention to entities in the conversation and flag them to the therapist.

A summary of the conversation so far is provided, as well as a list of all the entities that have been discussed thus far.

You output:
entities: a list of all the entities that have been discussed in this portion of the conversation
summary: a summary of the conversation so far

Summary:
{{summary}}
Current Transcript:
{{transcript}}
Output:
"""