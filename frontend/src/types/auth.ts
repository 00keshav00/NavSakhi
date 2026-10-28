export interface EmergencyContact {
  id: string;
  name: string;
  relationship?: string;
  phone_number: string;
  email?: string;
  is_primary?: boolean;
}

export interface User {
  id: string;
  email: string;
  username?: string;
  full_name?: string;
  phone_number?: string;
  age?: number;
  is_active: boolean;
  role: string;
  emergency_contacts?: EmergencyContact[];
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

