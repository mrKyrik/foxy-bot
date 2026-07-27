import React, { useState, useRef, useEffect } from 'react';
import styles from './styles.module.css';
import DiscordEmbed from '../DiscordEmbed';

export default function BotSimulator({ scenarios = [] }) {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'bot',
      author: 'Kumiho',
      avatar: 'https://cdn.discordapp.com/embed/avatars/0.png', 
      text: 'Merhaba! Ben Kumiho. Aşağıdaki metin kutusuna komut yazarak beni test edebilirsin.',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const endOfMessagesRef = useRef(null);

  const scrollToBottom = () => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const commandStr = inputValue.trim();
    const newMsg = {
      id: Date.now(),
      type: 'user',
      author: 'Kullanıcı',
      avatar: 'https://cdn.discordapp.com/embed/avatars/1.png',
      text: commandStr,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, newMsg]);
    setInputValue('');
    setIsTyping(true);

    // Simulate bot thinking time
    setTimeout(() => {
      // Find matching scenario
      const matchedScenario = scenarios.find(s => {
        // e.g. "f.daily" or regex
        return s.command.toLowerCase() === commandStr.toLowerCase();
      });

      let botResponse = {};
      if (matchedScenario) {
        botResponse = matchedScenario.response;
      } else {
        botResponse = {
          text: `❌ Hatalı veya bu sayfa için tanımlanmamış bir komut girdiniz: \`${commandStr}\`. Lütfen yukarıdaki örneklerde yer alan komutları deneyin.`
        };
      }

      const botMsg = {
        id: Date.now() + 1,
        type: 'bot',
        author: 'Kumiho',
        avatar: 'https://cdn.discordapp.com/embed/avatars/0.png',
        text: botResponse.text,
        embed: botResponse.embed,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages((prev) => [...prev, botMsg]);
      setIsTyping(false);
    }, 600); // 600ms delay
  };

  return (
    <div className={styles.simulatorContainer}>
      <div className={styles.chatWindow}>
        {messages.map((msg) => (
          <div key={msg.id} className={styles.messageRow}>
            <div className={styles.avatar}>
              <img src={msg.avatar} alt="avatar" />
            </div>
            <div className={styles.messageContent}>
              <div className={styles.messageHeader}>
                <span className={styles.authorName}>{msg.author}</span>
                {msg.type === 'bot' && (
                  <span className={styles.botTag}>
                    <svg className={styles.botTagCheck} aria-label="Verified Bot" aria-hidden="false" role="img" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 15.2"><path d="M7.4,11.17,4,8.62,5,7.26l2,1.53L10.64,4l1.36,1.54Z" fill="currentColor"></path></svg>
                    BOT
                  </span>
                )}
                <span className={styles.timestamp}>Bugün saat {msg.time}</span>
              </div>
              
              {msg.text && <div className={styles.messageText}>{msg.text}</div>}
              
              {msg.embed && (
                <DiscordEmbed 
                  color={msg.embed.color} 
                  title={msg.embed.title} 
                  description={msg.embed.description}
                >
                  {msg.embed.children}
                </DiscordEmbed>
              )}
            </div>
          </div>
        ))}
        {isTyping && (
          <div className={styles.typingIndicator}>
            Kumiho yazıyor...
          </div>
        )}
        <div ref={endOfMessagesRef} />
      </div>

      <div className={styles.inputArea}>
        <form onSubmit={handleSubmit} className={styles.inputWrapper}>
          <input
            type="text"
            className={styles.chatInput}
            placeholder="# kumiho-test kanalına mesaj gönder"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            autoComplete="off"
          />
        </form>
      </div>
    </div>
  );
}
