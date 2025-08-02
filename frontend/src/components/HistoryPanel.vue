<template>
  <div>
    <!-- 历史面板内容 -->
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'HistoryPanel',
  emits: ['new-chat', 'switch-chat', 'delete-chat'],
  setup(props, { emit }) {
    const createNewChat = () => {
      emit('new-chat');
    };

    const switchChat = (chat) => {
      emit('switch-chat', chat);
    };

    const deleteChat = (chatId) => {
      emit('delete-chat', chatId);
    };

    return {
      createNewChat,
      switchChat,
      deleteChat
    };
  }
});
</script>

<style scoped>
/* 历史面板样式 */
</style>