# OIDC Authentication Setup

Compass supports OpenID Connect (OIDC) for single sign-on (SSO) authentication. This guide explains how to configure and use OIDC providers.

## Supported Providers

- Azure AD / Azure AD B2C
- Okta
- Google Identity
- Any standards-compliant OIDC provider

## Configuration

### Environment Variables

OIDC providers are configured via environment variables in the format:

```
OIDC_<PROVIDER_NAME>=<provider_name>,<client_id>,<client_secret>,<discovery_url>,<redirect_uri>
```

### Example: Azure AD B2C

```bash
OIDC_AZURE_AD=azure,\
my-client-id,\
my-client-secret,\
https://mytenant.b2clogin.com/mytenant.onmicrosoft.com/b2c_1_signin/v2.0/.well-known/openid-configuration,\
http://localhost:8000/auth/callback
```

### Example: Okta

```bash
OIDC_OKTA=okta,\
my-client-id,\
my-client-secret,\
https://dev-12345.okta.com/.well-known/openid-configuration,\
http://localhost:8000/auth/callback
```

### Example: Google

```bash
OIDC_GOOGLE=google,\
my-client-id.apps.googleusercontent.com,\
my-client-secret,\
https://accounts.google.com/.well-known/openid-configuration,\
http://localhost:8000/auth/callback
```

## API Endpoints

### Start OIDC Flow

```
GET /auth/{provider}
```

Redirects user to the OIDC provider's authorization endpoint.

**Example:**
```
GET /auth/azure
```

### OIDC Callback

```
GET /auth/callback?code=<auth_code>&state=<state>
```

Handles the callback from the OIDC provider. Automatically exchanges the authorization code for tokens and creates a user session.

### Auth Success

```
GET /auth/success?token=<token>&user_id=<user_id>
```

Returns the authentication token and user ID after successful authentication.

## User Flow

1. **Frontend** redirects user to `/auth/{provider}`
2. **Compass** redirects to OIDC provider login page
3. **User** authenticates with provider
4. **Provider** redirects back to `/auth/callback`
5. **Compass** exchanges code for token, extracts user info
6. **Compass** redirects to `/auth/success` with token
7. **Frontend** stores token and makes authenticated API requests

## Fallback Authentication

If OIDC is not configured, Compass falls back to the simple `/login` endpoint with email/password authentication.

## User Claims Mapping

The following OIDC claims are mapped to Compass user fields:

| OIDC Claim | Compass Field | Required |
|------------|---------------|----------|
| `sub` or `user_id` | `user_id` | Yes |
| `email` | `email` | Yes |
| `name` | `name` | No |
| `roles` | `roles` | No |

If `roles` is not provided by the OIDC provider, the user defaults to `["user"]`.

## Token Management

- Tokens created at login are stored in memory (in-process)
- Tokens have a default expiry of 24 hours (configurable)
- Tokens are revoked on logout via `/logout` endpoint

## CSRF Protection

OIDC flows use state-based CSRF protection:
1. State is generated and stored before redirect
2. State is verified on callback
3. State is invalidated after use
4. Expired states (>10 minutes) are automatically cleaned up

## Troubleshooting

### "Unknown OIDC provider" error

- Verify the provider name in the OIDC_* environment variable matches the provider name in the request
- Verify all required environment variables are set

### "Invalid or expired state" error

- State may have expired (>10 minutes)
- CSRF token may have been reused
- Try initiating login again

### "Failed to authenticate" error

- Check that client credentials are correct
- Verify the OIDC provider's discovery URL is accessible
- Check that the redirect URI matches the configured value
- Ensure required claims (sub/user_id and email) are returned by the provider

## Production Considerations

- Use HTTPS in production (update redirect_uri accordingly)
- Securely manage client secrets (use secrets management tools)
- Implement token refresh for long-lived sessions
- Monitor OIDC authentication events
- Implement rate limiting on auth endpoints
