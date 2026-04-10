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

    // Create GitHub release
    "@semantic-release/github",

  ],
};