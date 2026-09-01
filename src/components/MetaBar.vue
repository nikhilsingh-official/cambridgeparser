<template>
    <div class="meta-container">
        <h1 class="page-header">Dashboard</h1>
        <!-- there is no profile route or menu yet. Disable the control
             instead of presenting a button that silently does nothing. -->
        <button
          class="profile-button"
          type="button"
          aria-label="Profile settings are not available yet"
          title="Profile settings are not available yet"
          disabled
        ></button>
    </div>
</template>
<style lang="scss" scoped>
.meta-container {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
}
.page-header {
    font-family: 'Inter';
    margin-right: auto;
}
.profile-button {
    margin-left: auto;
    height: 65%;
    aspect-ratio: 1/1;
    background-image: url(@/assets/icons/user.svg);
    background-size: 50% 50%;
    background-repeat: no-repeat;
    background-position: center center;
    border: none;
    background-color: transparent;
    cursor: not-allowed;
    opacity: 0.55;
}
</style>
