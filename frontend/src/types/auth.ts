export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  role: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  user: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
  remember_me?: boolean;
}
