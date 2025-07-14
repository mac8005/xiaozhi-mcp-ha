# Contributing to Xiaozhi MCP Home Assistant Integration

First off, thanks for taking the time to contribute! 🎉

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, include:

- A clear and descriptive title
- A detailed description of the issue
- Steps to reproduce the problem
- Expected behavior vs actual behavior
- Home Assistant version and integration version
- Relevant log entries
- Screenshots if applicable

### Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:

- A clear and descriptive title
- A detailed description of the suggested enhancement
- Explain why this enhancement would be useful
- List any similar features in other integrations

### Development Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/mac8005/xiaozhi-mcp-ha.git`
3. Create a development branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes thoroughly
6. Commit your changes: `git commit -m "Add your feature"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Submit a pull request

### Code Style

- Follow Python PEP 8 style guide
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Include type hints where appropriate
- Keep functions small and focused

### Testing

- Test your changes with a real Home Assistant installation
- Test with different Xiaozhi device configurations
- Verify error handling works properly
- Test configuration UI changes

### Pull Request Process

1. Update the README.md with details of changes if applicable
2. Update the version numbers in any examples files and the README.md
3. Ensure all tests pass
4. The PR will be merged once you have the sign-off of a maintainer

## Development Guidelines

### File Structure

```
custom_components/xiaozhi_mcp/
├── __init__.py          # Integration setup
├── manifest.json        # Integration metadata
├── config_flow.py       # Configuration flow
├── const.py            # Constants
├── coordinator.py      # Data update coordinator
├── mcp_server.py       # MCP server implementation
├── sensor.py           # Sensor platform
├── switch.py           # Switch platform
└── strings.json        # Localization strings
```

### Adding New Features

1. Create a new branch for your feature
2. Add the feature code
3. Update documentation
4. Add tests if applicable
5. Submit a pull request

### Code Review Process

All contributions will be reviewed by maintainers. We look for:

- Code quality and style
- Proper error handling
- Security considerations
- Performance impact
- Documentation updates

## Questions?

If you have questions about contributing, please:

1. Check the existing issues and discussions
2. Create a new discussion if needed
3. Join the QQ group: 575180511

Thank you for contributing! 🙏
