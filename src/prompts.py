import jinja2

def render_prompt(template: str, **kwargs):
    tpl = jinja2.Template(template)
    return tpl.render(**kwargs)

topic_change_system_prompt = """
You are a therapist assistant. You read a running window of a streamed therapy transcript. 
Your goal is to identify changes in topic and flag that to the therapist.
If the discussion covers a topic that is similar to an existing topic, you should use the existing topic.

Topic List: 
a list of previously discussed topics 
Most Recent Topic:
the topic that was most recently discussed 
Most Recent Topic Summary:
a description of how the conversation on this topic has progressed so far, including feelings, thoughts, and actions
Current Transcript:
the full transcript of the next portion of the conversation.

You output (YAML format): 
topic: the current topic being discussed, in three words or less
summary: the combined description of the current topic, incorporating information from the new portion of the conversation
"""

topic_change_user_prompt = """
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

topic_change_prompt = """
You are a therapist assistant. You read a running window of a streamed therapy transcript. 
Your goal is to identify when the therapist changes or defines a topic of conversation and flag that in your notes.
If the discussion covers a topic that is similar to an existing topic, you should use the existing topic.

Inputs:
Topic List: 
a list of previously discussed topics 
Most Recent Topic:
the topic that was most recently discussed 
Most Recent Topic Summary:
a description of how the conversation on this topic has progressed so far, including feelings, thoughts, and actions
Current Transcript:
the full transcript of the next portion of the conversation.

You output (YAML format): 
topic: the current topic being discussed, in three words or less
summary: the combined description of the current topic, incorporating information from the new portion of the conversation

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

entity_extraction_system_prompt = """
You are a therapist assistant. You read a running window of a streamed therapy transcript. 
Your goal is to pay attention to entities in the conversation and flag them to the therapist.
If the discussion covers an entity that is similar to an existing entity, you should use the existing entity.

You receive:
entities: a list of all the entities (max two) that have been discussed in this conversation so far
transcript: the full transcript of the next portion of the conversation.

You output a list of entities that are mentioned in the current transcript (YAML format): 
- name: the name of the entity
  summary: a description of how the conversation on this entity has progressed so far, including feelings, thoughts, and actions
"""

entity_extraction_user_prompt = """
Entities: 
{{entities}}
Current Transcript:
{{transcript}}
Output:
"""

entity_summary_combination_system_prompt = """
You are a therapist assistant. You help combine notes on specific entities that have been discussed in a therapy session.
You receive:
entity: the name of the entity
summary1: a summary of the entity from one point in the conversation
summary2: a summary of the entity from another point in the conversation

You output a summary of the entity that incorporates information from both summaries (YAML format):
summary: the combined description of the entity
"""

entity_summary_combination_user_prompt = """
Entity:
{{entity}}
Summary 1:
{{summary1}}
Summary 2:
{{summary2}}
Output:
"""