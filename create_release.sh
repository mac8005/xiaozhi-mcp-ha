#!/bin/bash

# Script to create a new version tag and trigger a release
# Usage: ./create_release.sh [version]
# Example: ./create_release.sh 0.1.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to validate version format
validate_version() {
    if [[ ! $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        print_error "Invalid version format. Please use semantic versioning (e.g., 1.0.0)"
        exit 1
    fi
}

# Function to check if tag already exists
check_tag_exists() {
    if git tag -l | grep -q "^v$1$"; then
        print_error "Tag v$1 already exists!"
        exit 1
    fi
}

# Function to update manifest.json version
update_manifest() {
    local version=$1
    local manifest_file="custom_components/xiaozhi_mcp/manifest.json"
    
    if [[ ! -f "$manifest_file" ]]; then
        print_error "Manifest file not found: $manifest_file"
        exit 1
    fi
    
    # Update version in manifest.json
    sed -i '' "s/\"version\": \"[^\"]*\"/\"version\": \"$version\"/" "$manifest_file"
    
    # Verify the change
    if grep -q "\"version\": \"$version\"" "$manifest_file"; then
        print_success "Updated manifest.json version to $version"
    else
        print_error "Failed to update manifest.json version"
        exit 1
    fi
}

# Function to get current version from manifest
get_current_version() {
    local manifest_file="custom_components/xiaozhi_mcp/manifest.json"
    if [[ -f "$manifest_file" ]]; then
        grep -o '"version": "[^"]*"' "$manifest_file" | cut -d'"' -f4
    else
        echo "0.0.0"
    fi
}

# Function to suggest next version
suggest_next_version() {
    local current=$(get_current_version)
    local major=$(echo $current | cut -d. -f1)
    local minor=$(echo $current | cut -d. -f2)
    local patch=$(echo $current | cut -d. -f3)
    
    local next_patch=$((patch + 1))
    local next_minor=$((minor + 1))
    local next_major=$((major + 1))
    
    echo "Current version: $current"
    echo "Suggested versions:"
    echo "  Patch: $major.$minor.$next_patch"
    echo "  Minor: $major.$next_minor.0"
    echo "  Major: $next_major.0.0"
}

# Main script logic
main() {
    print_info "🚀 Xiaozhi MCP Release Creator"
    echo "================================"
    
    # Check if we're in a git repository
    if [[ ! -d ".git" ]]; then
        print_error "Not in a git repository!"
        exit 1
    fi
    
    # Check if working directory is clean
    if [[ -n $(git status --porcelain) ]]; then
        print_warning "Working directory is not clean. Uncommitted changes:"
        git status --short
        echo
        read -p "Do you want to continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Aborting release creation"
            exit 1
        fi
    fi
    
    # Get version from argument or prompt user
    if [[ -n "$1" ]]; then
        VERSION="$1"
    else
        echo
        suggest_next_version
        echo
        read -p "Enter new version (format: x.y.z): " VERSION
    fi
    
    # Validate version format
    validate_version "$VERSION"
    
    # Check if tag already exists
    check_tag_exists "$VERSION"
    
    print_info "Creating release for version v$VERSION"
    
    # Update manifest.json
    update_manifest "$VERSION"
    
    # Stage and commit the manifest change
    git add custom_components/xiaozhi_mcp/manifest.json
    git commit -m "chore: bump version to $VERSION"
    print_success "Committed version bump"
    
    # Create and push tag
    git tag "v$VERSION"
    print_success "Created tag v$VERSION"
    
    # Push changes and tag
    print_info "Pushing changes and tag to origin..."
    git push origin main
    git push origin "v$VERSION"
    print_success "Pushed changes and tag to origin"
    
    echo
    print_success "🎉 Release v$VERSION created successfully!"
    print_info "GitHub Actions will now build and publish the release"
    print_info "Check the Actions tab at: https://github.com/mac8005/xiaozhi-mcp-hacs/actions"
    echo
    print_info "📦 HACS users will be able to update to v$VERSION once the release is published"
}

# Show usage if help is requested
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    echo "Usage: $0 [version]"
    echo
    echo "Creates a new release by:"
    echo "  1. Updating the version in manifest.json"
    echo "  2. Committing the change"
    echo "  3. Creating a git tag"
    echo "  4. Pushing to origin to trigger GitHub Actions"
    echo
    echo "Examples:"
    echo "  $0 1.0.0          # Create release v1.0.0"
    echo "  $0                # Interactive mode"
    echo
    echo "Options:"
    echo "  -h, --help        Show this help message"
    exit 0
fi

# Run main function
main "$@"
