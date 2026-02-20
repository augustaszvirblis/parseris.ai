import { Button } from "antd";
import { Row, Col } from "antd";

import { getBaseUrl } from "../../helpers/GetStaticData";
import "./Login.css";

let LoginForm = null;
try {
  LoginForm = require("../../plugins/login-form/LoginForm").LoginForm;
} catch {
  // The components will remain null of it is not available
}

function Login() {
  const baseUrl = getBaseUrl();
  const newURL = baseUrl + "/api/v1/login";
  const handleLogin = () => {
    window.location.href = newURL;
  };

  return (
    <div className="login-main">
      <Row>
        {LoginForm ? (
          <LoginForm handleLogin={handleLogin} />
        ) : (
          <Col xs={24} className="login-center-section">
            <div className="button-wraper">
              <h1 className="logo logo-text">Parseris.ai</h1>
              <p className="open-source-subtitle">
                Parseris.ai is open-source on{" "}
                <a
                  href="https://github.com/augustaszvirblis/parseris.ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="github-link"
                >
                  GitHub
                </a>
              </p>
              <div className="login-button-wrap">
                <Button
                  className="login-button button-margin"
                  onClick={handleLogin}
                >
                  Sign up / Log in
                </Button>
              </div>
            </div>
          </Col>
        )}
      </Row>
    </div>
  );
}

export { Login };
