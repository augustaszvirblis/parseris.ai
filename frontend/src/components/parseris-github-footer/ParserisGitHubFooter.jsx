import config from "../../config";
import "./ParserisGitHubFooter.css";

const GITHUB_URL = "https://github.com/augustaszvirblis/parseris.ai";

function isParseris() {
  if (config.appName === "Parseris.ai") return true;
  if (
    typeof window !== "undefined" &&
    window.location?.hostname?.includes("parseris")
  ) {
    return true;
  }
  if (process.env.REACT_APP_APP_NAME === "Parseris.ai") return true;
  return false;
}

function ParserisGitHubFooter() {
  if (!isParseris()) {
    return null;
  }

  return (
    <footer className="parseris-github-footer">
      <a
        href={GITHUB_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="parseris-github-footer__link"
      >
        Parseris.ai is open-source on GitHub
      </a>
    </footer>
  );
}

export { ParserisGitHubFooter };
