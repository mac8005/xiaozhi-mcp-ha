"""Test that imports work correctly."""

def test_import_integration():
    """Test that we can import the integration."""
    from custom_components.xiaozhi_mcp import async_setup_entry, async_unload_entry
    from custom_components.xiaozhi_mcp.const import DOMAIN
    
    assert DOMAIN == "xiaozhi_mcp"
    assert async_setup_entry is not None
    assert async_unload_entry is not None

def test_import_config_flow():
    """Test that we can import the config flow."""
    from custom_components.xiaozhi_mcp.config_flow import ConfigFlow
    from custom_components.xiaozhi_mcp.const import DOMAIN
    
    assert ConfigFlow.VERSION == 1
    assert hasattr(ConfigFlow, 'async_step_user')
