import { defineStore } from 'pinia'
import { createClient } from '@supabase/supabase-js'
import { ref } from 'vue'
import type { Session } from '@supabase/supabase-js'
import type { Ref } from 'vue'
import router from '@/router/router'

export const supabase = createClient("http://127.0.0.1:54321", "sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH")

export type EmailLoginOptions = { email: string; password: string; }
export type OAuthLoginOptions = { provider: 'google' | 'azure' | 'twitter' }
export type LoginOptions = EmailLoginOptions | OAuthLoginOptions;

export const useAuthStore = defineStore("auth", () => {
  const session: Ref<Session | null> = ref(null);
  const jwt = session.value?.access_token;

  async function init() {
    const { data } = await supabase.auth.getSession();
    session.value = data.session;

    supabase.auth.onAuthStateChange((_event, newSession) => {
      session.value = newSession;
    });
  }
  
  async function login(choice: LoginOptions, redirect?: string) {
    
    const oauthOptions = redirect
      ? { redirectTo: `${location.origin}/${redirect}` }
      : undefined;

    if ("email" in choice) {
      console.log("Logging in with email and password...")
      const { data, error } = await supabase.auth.signInWithPassword({
        email: choice.email,
        password: choice.password,
      });
      if (error) throw error;
      console.log(data);
      router.push("/")
      return data;
    }

    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: choice.provider,
      options: oauthOptions,
    });
    if (error) throw error;
    return data;
  }

  async function logout() {
    await supabase.auth.signOut()
    session.value = null
  }

  return { session, jwt, init, login, logout }
})