<template>
    <button @click="routerPushLogin({ provider: 'google' })" id="google-login" class="auth-login">Google</button>
    <button @click="routerPushLogin({ provider: 'twitter' })" id="twitter-login" class="auth-login">Twitter</button>
    <button @click="routerPushLogin({ provider: 'azure' })" id="azure-login" class="auth-login">Azure</button>
    <input v-model="email" id="email-input" placeholder="Email..."></input>
    <input v-model="password" id="password-input" placeholder="Password..."></input>
    <button :disabled="loading" @click="routerPushLogin({ email, password })" id="submit-email-pwd">Submit</button>
</template>
<script lang="ts" setup>
import { ref } from 'vue';
import { useAuthStore, type LoginOptions } from '@/stores/useAuth';

const email = ref("nikhilabrolsingh11@gmail.com");
const password = ref("REMOVED_HISTORICAL_PASSWORD");

const { login } = useAuthStore();

const loading = ref(false);
async function routerPushLogin(options: LoginOptions) {
    if ('provider' in options) {
        await login(options, "dashboard");
        return;
    }

    loading.value = true;
    try {
        console.log("Logging in email: ", email.value, " and password: ", password.value)
        await login(options);
    } finally {
        loading.value = false;
    }
}

</script>