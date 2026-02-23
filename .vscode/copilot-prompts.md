# Copilot Prompts for Identifying Next Prioritized Item

## Instructions for VSCode
- Ensure you have the GitHub Copilot extension installed and activated in VSCode.
- Create a new file in your project directory and paste the prompt below to use it directly with Copilot.

## Prompt
"Given the current backlog of items, please identify the next prioritized item based on the following analysis requirements."

## Analysis Requirements
1. **Business Value**: Consider the potential impact on stakeholders and any metrics that indicate the item's importance.
2. **Effort Estimation**: Analyze the time and resources required to complete the item.
3. **Dependencies**: Identify any dependencies that might affect the development of the prioritized item.
4. **Team Capacity**: Assess the current workload of team members to determine if the item aligns with their capacity.

## Expected Output Format
```json
{
  "next_item": {
    "title": "[Title of the next prioritized item]",
    "reason": "[Rationale for prioritization]",
    "business_value": [Low | Medium | High],
    "effort_estimation": "[Effort required]",
    "dependencies": ["[List of dependencies]"],
    "assigned_to": "[Team member]"
  }
}
```

## Test Commands
- Run `npm test` to execute the unit tests and ensure the functionality works as expected.
- Validate the output format using your preferred JSON validator to ensure correctness.

---