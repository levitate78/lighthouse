module.exports = {
  branches: ["main"],

  plugins: [
    // Analyze commit messages (feat, fix, BREAKING CHANGE, etc.)
    [
      "@semantic-release/commit-analyzer",
      {
        preset: "angular",
      },
    ],

    // Generate release notes from commits
    [
      "@semantic-release/release-notes-generator",
      {
        preset: "angular",
      },
    ],

    // Write/update CHANGELOG.md
    [
      "@semantic-release/changelog",
      {
        changelogFile: "CHANGELOG.md",
      },
    ],

    // Create GitHub release
    "@semantic-release/github",

    // Commit CHANGELOG.md back to the repository
    [
      "@semantic-release/git",
      {
        assets: ["CHANGELOG.md"],
        message:
          "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}",
      },
    ],
  ],
};