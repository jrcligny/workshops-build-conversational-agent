<!--
Compaction prompt of your agent (workshop 08). Your harness loads this file when it compacts
and removes these HTML comments; the rest is the system message of the separate model call
that writes the summary, and appears in the trace as compaction.system_prompt.

It is not the agent's system prompt: here the model does not converse, it summarizes. In
French, it asks for a summary under five fixed headings, in this order:
  Objectif de l'utilisateur / Entités en cours / Faits établis / Décisions et choix confirmés /
  Questions en suspens
Facts keep their source (which tool read them). The summary is rolling: the model receives the
previous summary and the turns that leave the context, and returns the updated summary.
-->
