# Examples and Use Cases

## Voice Commands

Once your Xiaozhi device is connected, you can use natural language commands:

### Lighting Control

- "Turn on the living room lights"
- "Set bedroom lights to 50%"
- "Turn off all lights"
- "Make the kitchen lights blue"

### Climate Control

- "Set the temperature to 72 degrees"
- "Turn on the air conditioning"
- "What's the current temperature?"
- "Turn off the heater"

### Device Status

- "Is the front door locked?"
- "What's the humidity in the bathroom?"
- "Are any windows open?"
- "Check the security system status"

### Scenes and Automations

- "Activate movie mode"
- "Turn on bedtime scene"
- "Start morning routine"
- "Set party lights"

## Automation Examples

### Xiaozhi Connection Status Automation

```yaml
# automation.yaml
- id: xiaozhi_connection_alert
  alias: "Xiaozhi Connection Alert"
  trigger:
    - platform: state
      entity_id: sensor.xiaozhi_mcp_status
      to: "Disconnected"
      for: "00:05:00"
  action:
    - service: notify.mobile_app_your_phone
      data:
        title: "Xiaozhi Disconnected"
        message: "Xiaozhi has been disconnected for 5 minutes"
```

### Voice Command Response

```yaml
# automation.yaml
- id: xiaozhi_voice_response
  alias: "Xiaozhi Voice Response"
  trigger:
    - platform: event
      event_type: xiaozhi_mcp_message_received
  condition:
    - condition: template
      value_template: "{{ trigger.event.data.message_type == 'voice_command' }}"
  action:
    - service: tts.google_translate_say
      data:
        entity_id: media_player.living_room_speaker
        message: "Command executed successfully"
```

## Service Calls

### Reconnect Service

```yaml
# script.yaml
reconnect_xiaozhi:
  alias: "Reconnect Xiaozhi"
  sequence:
    - service: xiaozhi_mcp.reconnect
```

### Send Message Service

```yaml
# script.yaml
send_xiaozhi_message:
  alias: "Send Message to Xiaozhi"
  sequence:
    - service: xiaozhi_mcp.send_message
      data:
        message: "Hello from Home Assistant!"
```

## Dashboard Cards

### Status Card

```yaml
# dashboard.yaml
type: entities
title: Xiaozhi MCP Status
entities:
  - entity: sensor.xiaozhi_mcp_status
    name: Connection Status
  - entity: sensor.xiaozhi_mcp_last_seen
    name: Last Seen
  - entity: sensor.xiaozhi_mcp_message_count
    name: Messages
  - entity: sensor.xiaozhi_mcp_error_count
    name: Errors
```

### Control Card

```yaml
# dashboard.yaml
type: entities
title: Xiaozhi MCP Control
entities:
  - entity: switch.xiaozhi_mcp_connection
    name: Connection
  - entity: switch.xiaozhi_mcp_debug_logging
    name: Debug Logging
```

### History Graph

```yaml
# dashboard.yaml
type: history-graph
title: Xiaozhi MCP Activity
entities:
  - sensor.xiaozhi_mcp_message_count
  - sensor.xiaozhi_mcp_error_count
hours_to_show: 24
```

## Advanced Use Cases

### Smart Home Scenes

Create complex scenes that can be triggered by voice:

```yaml
# scenes.yaml
- id: movie_night
  name: "Movie Night"
  entities:
    light.living_room_lights:
      state: on
      brightness: 30
      color_name: red
    media_player.tv:
      state: on
      source: "Netflix"
    climate.living_room:
      state: on
      temperature: 68
    cover.living_room_blinds:
      state: closed
```

### Conditional Responses

```yaml
# automation.yaml
- id: xiaozhi_conditional_response
  alias: "Xiaozhi Conditional Response"
  trigger:
    - platform: event
      event_type: xiaozhi_mcp_tool_called
  condition:
    - condition: template
      value_template: "{{ trigger.event.data.tool == 'get_state' }}"
  action:
    - choose:
        - conditions:
            - condition: template
              value_template: "{{ trigger.event.data.entity_id.startswith('light.') }}"
          sequence:
            - service: xiaozhi_mcp.send_message
              data:
                message: "Light status retrieved"
        - conditions:
            - condition: template
              value_template: "{{ trigger.event.data.entity_id.startswith('sensor.') }}"
          sequence:
            - service: xiaozhi_mcp.send_message
              data:
                message: "Sensor reading obtained"
```

### Multi-Device Coordination

```yaml
# automation.yaml
- id: xiaozhi_multi_device
  alias: "Xiaozhi Multi-Device Control"
  trigger:
    - platform: event
      event_type: xiaozhi_mcp_message_received
      event_data:
        command: "goodnight"
  action:
    - service: scene.turn_on
      target:
        entity_id: scene.bedtime
    - service: alarm_control_panel.alarm_arm_night
      target:
        entity_id: alarm_control_panel.home_security
    - service: xiaozhi_mcp.send_message
      data:
        message: "Goodnight mode activated. All devices secured."
```

## Error Handling

### Connection Recovery

```yaml
# automation.yaml
- id: xiaozhi_auto_reconnect
  alias: "Xiaozhi Auto Reconnect"
  trigger:
    - platform: numeric_state
      entity_id: sensor.xiaozhi_mcp_error_count
      above: 5
  action:
    - service: xiaozhi_mcp.reconnect
    - delay: "00:01:00"
    - service: notify.persistent_notification
      data:
        title: "Xiaozhi Reconnected"
        message: "Xiaozhi MCP connection has been restored"
```

### Debug Information

```yaml
# automation.yaml
- id: xiaozhi_debug_info
  alias: "Xiaozhi Debug Info"
  trigger:
    - platform: state
      entity_id: sensor.xiaozhi_mcp_status
      to: "Disconnected"
  action:
    - service: system_log.write
      data:
        message: "Xiaozhi disconnected - Last seen: {{ states('sensor.xiaozhi_mcp_last_seen') }}, Errors: {{ states('sensor.xiaozhi_mcp_error_count') }}"
        level: warning
```

## Integration with Other Services

### Telegram Bot Integration

```yaml
# automation.yaml
- id: xiaozhi_telegram_status
  alias: "Xiaozhi Telegram Status"
  trigger:
    - platform: state
      entity_id: sensor.xiaozhi_mcp_status
  action:
    - service: notify.telegram
      data:
        title: "Xiaozhi Status Update"
        message: "Xiaozhi is now {{ states('sensor.xiaozhi_mcp_status') }}"
```

### Node-RED Integration

Create a Node-RED flow that:

1. Listens for Xiaozhi events
2. Processes natural language commands
3. Triggers complex automations
4. Provides voice feedback

This integration works seamlessly with Node-RED's Home Assistant nodes for advanced automation scenarios.
