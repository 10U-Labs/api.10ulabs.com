import {
  to = aws_ses_email_identity.contact
  id = "contact@10ulabs.com"
}

resource "aws_ses_email_identity" "contact" {
  email = local.contact_email
}

resource "aws_ssm_parameter" "recaptcha_secret" {
  name        = local.parameter_name
  description = "Google reCAPTCHA v3 secret key the contact submissions handler verifies tokens against."
  type        = "SecureString"
  value       = var.recaptcha_secret_key
}
