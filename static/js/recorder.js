/**
 * SpeakPro AI – Safe Space Speech Practice Studio
 * Implements Topic Roulette Wheel Subtopic Picker, Target Speech Duration Selector,
 * Web Audio API waveform visualizer, countdown timer, Web Speech API transcription,
 * and AJAX submission to Google Gemini AI speech evaluator.
 */

let mediaRecorder = null;
let audioChunks = [];
let audioBlob = null;
let audioContext = null;
let analyserNode = null;
let animationFrameId = null;
let recognition = null;
let isRecording = false;
let speechTimerInterval = null;
let elapsedSeconds = 0;
let currentTopicId = null;
let currentTopicTitle = "Describe your greatest personal or professional achievement and what it taught you about leadership.";
let currentCategory = "general";
let currentDifficulty = "Intermediate";

// Default target speaking duration is 60 seconds (1 minute)
window.selectedDurationSeconds = 60;
window.selectedLanguage = "en-US";
let isRouletteSpinning = false;

// Real-Time Acoustic Telemetry & Pause Tracking Variables
let liveWpm = 0;
let dramaticPausesCount = 0;
let hesitationPausesCount = 0;
let totalSpeakingSeconds = 0;
let totalPauseSeconds = 0;
let isCurrentlyPaused = false;
let pauseStartTime = 0;
let pauseTrackerInterval = null;

// Visual Presence Tracker
let webcamAnalyzer = null;
let visualMetricsData = null;

/**
 * RICH CURATED SUBTOPICS LIBRARY FOR TOPIC ROULETTE EFFECT
 * Over 60 subtopics across 6 distinct categories in English, Hindi, and Malayalam
 */
const TOPIC_ROULETTE_LIBRARY = {
  technology: [
    { title: "How will generative AI transform the job market over the next decade?", category: "AI & Technology", difficulty: "Advanced" },
    { title: "Should artificial intelligence models be granted legal rights or personhood in the future?", category: "AI & Technology", difficulty: "Expert" },
    { title: "The ethical responsibility of software developers when building autonomous decision systems.", category: "AI & Technology", difficulty: "Advanced" },
    { title: "Explain how a neural network works to an audience with no technical background.", category: "AI & Technology", difficulty: "Intermediate" },
    { title: "The biggest cybersecurity challenge facing global financial institutions today.", category: "AI & Technology", difficulty: "Advanced" },
    { title: "Will artificial intelligence enhance human creativity or diminish original thought?", category: "AI & Technology", difficulty: "Intermediate" },
    { title: "How cloud computing and edge AI are reshaping modern infrastructure.", category: "AI & Technology", difficulty: "Intermediate" },
    { title: "The balance between user privacy and data-driven personalization in consumer tech.", category: "AI & Technology", difficulty: "Advanced" },
    { title: "Should open-source AI models be strictly regulated by international governments?", category: "AI & Technology", difficulty: "Expert" },
    { title: "How autonomous robotics will change healthcare and robotic surgery.", category: "AI & Technology", difficulty: "Intermediate" }
  ],
  science: [
    { title: "The most revolutionary scientific discovery of the 21st century so far.", category: "Science & Future", difficulty: "Intermediate" },
    { title: "Why human space exploration and Mars missions matter for the long-term survival of humanity.", category: "Science & Future", difficulty: "Advanced" },
    { title: "How biotechnology and gene editing could eliminate hereditary human diseases.", category: "Science & Future", difficulty: "Advanced" },
    { title: "The role of clean energy transition in mitigating global climate change.", category: "Science & Future", difficulty: "Intermediate" },
    { title: "The search for extraterrestrial intelligence: What happens if we discover we are not alone?", category: "Science & Future", difficulty: "Intermediate" },
    { title: "How quantum computing will revolutionize scientific simulation and encryption.", category: "Science & Future", difficulty: "Expert" },
    { title: "The critical importance of biodiversity conservation for ocean ecosystems.", category: "Science & Future", difficulty: "Intermediate" },
    { title: "How advances in neuroscience are changing our understanding of human consciousness.", category: "Science & Future", difficulty: "Advanced" },
    { title: "Why investing in basic scientific research is essential for economic prosperity.", category: "Science & Future", difficulty: "Intermediate" },
    { title: "The promise and challenges of nuclear fusion as a limitless clean energy source.", category: "Science & Future", difficulty: "Advanced" }
  ],
  leadership: [
    { title: "How to lead and motivate a cross-functional team through high uncertainty and change.", category: "Executive Leadership", difficulty: "Advanced" },
    { title: "The core differences between being a tactical manager and a strategic executive leader.", category: "Executive Leadership", difficulty: "Advanced" },
    { title: "How to pitch a high-risk, high-reward innovation to skeptical board members.", category: "Executive Leadership", difficulty: "Expert" },
    { title: "Handling a public company crisis while maintaining stakeholder trust and morale.", category: "Executive Leadership", difficulty: "Expert" },
    { title: "The role of emotional intelligence and empathy in modern executive leadership.", category: "Executive Leadership", difficulty: "Intermediate" },
    { title: "Building a culture of psychological safety and accountability in the workplace.", category: "Executive Leadership", difficulty: "Advanced" },
    { title: "How to give difficult, constructive feedback without demoralizing an employee.", category: "Executive Leadership", difficulty: "Intermediate" },
    { title: "Why effective delegation is the most difficult skill for ambitious leaders to learn.", category: "Executive Leadership", difficulty: "Intermediate" },
    { title: "How to foster innovation and risk-taking in a traditionally risk-averse organization.", category: "Executive Leadership", difficulty: "Advanced" },
    { title: "The importance of transparent communication during corporate restructuring.", category: "Executive Leadership", difficulty: "Advanced" }
  ],
  general: [
    { title: "Describe your greatest personal or professional achievement and what it taught you about perseverance.", category: "Personal Growth", difficulty: "Intermediate" },
    { title: "A mentor or book that fundamentally transformed your perspective on success.", category: "Personal Growth", difficulty: "Intermediate" },
    { title: "How you overcame a significant failure or professional setback in your career.", category: "Personal Growth", difficulty: "Intermediate" },
    { title: "What does authentic leadership and personal success mean to you?", category: "Personal Growth", difficulty: "Beginner" },
    { title: "A skill you learned recently that changed how you approach daily challenges.", category: "Personal Growth", difficulty: "Beginner" },
    { title: "The importance of maintaining resilience and mental clarity under high pressure.", category: "Personal Growth", difficulty: "Intermediate" },
    { title: "Why continuous self-reflection is essential for long-term career satisfaction.", category: "Personal Growth", difficulty: "Beginner" },
    { title: "How to balance intense professional ambition with personal well-being.", category: "Personal Growth", difficulty: "Intermediate" },
    { title: "A time when you had to step outside your comfort zone to achieve an important goal.", category: "Personal Growth", difficulty: "Beginner" },
    { title: "The single most important lesson you have learned about teamwork and trust.", category: "Personal Growth", difficulty: "Intermediate" }
  ],
  business: [
    { title: "Should global corporations prioritize shareholder profit or social responsibility?", category: "Business & Ethics", difficulty: "Advanced" },
    { title: "The future of remote and hybrid work: Increasing autonomy versus office culture.", category: "Business & Ethics", difficulty: "Intermediate" },
    { title: "How to navigate ethical dilemmas when corporate targets conflict with personal values.", category: "Business & Ethics", difficulty: "Advanced" },
    { title: "The impact of ethical branding and sustainability on modern consumer trust.", category: "Business & Ethics", difficulty: "Intermediate" },
    { title: "Why transparency is the most undervalued currency in modern business relationships.", category: "Business & Ethics", difficulty: "Intermediate" },
    { title: "How artificial intelligence is changing customer relationship management and sales.", category: "Business & Ethics", difficulty: "Intermediate" },
    { title: "The ethical implications of data harvesting in personalized advertising.", category: "Business & Ethics", difficulty: "Advanced" },
    { title: "Why diversity of thought is critical for boardroom decision making.", category: "Business & Ethics", difficulty: "Advanced" },
    { title: "How startups can disrupt established corporate monopolies through speed and focus.", category: "Business & Ethics", difficulty: "Intermediate" },
    { title: "The future of global supply chains in an increasingly decentralized world economy.", category: "Business & Ethics", difficulty: "Advanced" }
  ],
  fun: [
    { title: "Convince a room of investors that time travel should be commercialized.", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "Pitch a bizarre invention that solves a very minor everyday annoyance.", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "Why pineapple on pizza is either a culinary masterpiece or an unmitigated disaster.", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "If you could invite three historical figures to dinner, who would you choose and why?", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "Explain the rules of a complex sport as if the audience has never visited Earth.", category: "Impromptu Fun", difficulty: "Intermediate" },
    { title: "Why cats or dogs would make superior heads of state in an ideal society.", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "Defend an unpopular movie or song with serious academic passion.", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "Give an impromptu toast to celebrating everyday ordinary moments in life.", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "Why waking up early is either the secret to success or a conspiracy.", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "Imagine you are the first ambassador sent to negotiate with an alien civilization.", category: "Impromptu Fun", difficulty: "Intermediate" }
  ]
};

const TOPIC_ROULETTE_LIBRARY_HI = {
  technology: [
    { title: "क्या आर्टिफिशियल इंटेलिजेंस अगले 10 वर्षों में भारत में नौकरियों का भविष्य बदल देगा?", category: "AI & Technology", difficulty: "Advanced" },
    { title: "साइबर सुरक्षा में आज दुनिया के सामने सबसे बड़ी चुनौतियां क्या हैं?", category: "AI & Technology", difficulty: "Advanced" },
    { title: "क्या भविष्य में एआई और मानव रचनात्मकता एक साथ काम कर पाएंगे?", category: "AI & Technology", difficulty: "Intermediate" },
    { title: "क्लाउड कंप्यूटिंग और आधुनिक तकनीक भारत के विकास में क्या योगदान दे रहे हैं?", category: "AI & Technology", difficulty: "Intermediate" },
    { title: "ऑनलाइन गोपनीयता और व्यक्तिगत डेटा सुरक्षा के बीच संतुलन कैसे बनाए रखें?", category: "AI & Technology", difficulty: "Advanced" }
  ],
  science: [
    { title: "इक्कीसवीं सदी की सबसे महत्वपूर्ण वैज्ञानिक खोज क्या है?", category: "Science & Future", difficulty: "Intermediate" },
    { title: "जलवायु परिवर्तन को रोकने के लिए स्वच्छ ऊर्जा क्यों आवश्यक है?", category: "Science & Future", difficulty: "Intermediate" },
    { title: "अंतरिक्ष अनुसंधान और चंद्रयान मिशन मानवता के लिए क्यों महत्वपूर्ण हैं?", category: "Science & Future", difficulty: "Advanced" },
    { title: "वैज्ञानिक अनुसंधान और अनुसंधान में निवेश देश की समृद्धि के लिए क्यों जरूरी है?", category: "Science & Future", difficulty: "Intermediate" },
    { title: "भविष्य में क्वांटम कंप्यूटिंग विज्ञान और सुरक्षा को कैसे बदलेगी?", category: "Science & Future", difficulty: "Expert" }
  ],
  leadership: [
    { title: "अनिश्चितता के समय में अपनी टीम का नेतृत्व और प्रेरणा कैसे दें?", category: "Executive Leadership", difficulty: "Advanced" },
    { title: "एक अच्छे प्रबंधक और एक महान रणनीतिक नेता में क्या अंतर है?", category: "Executive Leadership", difficulty: "Advanced" },
    { title: "कार्यस्थल पर आपसी विश्वास और ईमानदारी का माहौल कैसे बनाएं?", category: "Executive Leadership", difficulty: "Intermediate" },
    { title: "किसी संकट के समय धैर्य और आत्मविश्वास कैसे बनाए रखें?", category: "Executive Leadership", difficulty: "Expert" },
    { title: "प्रभावी संवाद किसी भी संगठन की सफलता का मूल मंत्र क्यों है?", category: "Executive Leadership", difficulty: "Intermediate" }
  ],
  general: [
    { title: "अपने जीवन की सबसे बड़ी व्यक्तिगत या व्यावसायिक उपलब्धि के बारे में बताएं।", category: "Personal Growth", difficulty: "Intermediate" },
    { title: "आपके जीवन का एक ऐसा अनुभव जिसने आपको असफलता से लड़ना सिखाया।", category: "Personal Growth", difficulty: "Intermediate" },
    { title: "आपके अनुसार सच्चे नेतृत्व और सफलता का वास्तविक अर्थ क्या है?", category: "Personal Growth", difficulty: "Beginner" },
    { title: "मानसिक शांति और व्यावसायिक सफलता के बीच संतुलन कैसे बनाएं?", category: "Personal Growth", difficulty: "Intermediate" },
    { title: "जीवन में लगातार सीखना और स्वयं का विकास क्यों महत्वपूर्ण है?", category: "Personal Growth", difficulty: "Beginner" }
  ],
  business: [
    { title: "क्या वैश्विक कंपनियों को लाभ से अधिक सामाजिक जिम्मेदारी को महत्व देना चाहिए?", category: "Business & Ethics", difficulty: "Advanced" },
    { title: "रिमोट और हाइब्रिड काम करने के तरीके से व्यवसाय पर क्या प्रभाव पड़ा है?", category: "Business & Ethics", difficulty: "Intermediate" },
    { title: "आधुनिक व्यवसाय में ग्राहक का विश्वास जीतना क्यों सबसे जरूरी है?", category: "Business & Ethics", difficulty: "Intermediate" },
    { title: "व्यवसाय में ईमानदारी और पारदर्शिता सबसे मूल्यवान संपत्ति क्यों है?", category: "Business & Ethics", difficulty: "Advanced" },
    { title: "स्टार्टअप्स नई सोच और तेजी से बड़े उद्योगों को कैसे चुनौती दे रहे हैं?", category: "Business & Ethics", difficulty: "Intermediate" }
  ],
  fun: [
    { title: "कल्पना करें कि आप समय यात्रा कर सकते हैं, आप किस ऐतिहासिक काल में जाएंगे और क्यों?", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "अगर आपको किसी परग्रही सभ्यता से बात करने का पहला मौका मिले, तो आप क्या कहेंगे?", category: "Impromptu Fun", difficulty: "Intermediate" },
    { title: "सुबह जल्दी उठना सफलता की कुंजी है या सिर्फ एक भ्रम?", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "इतिहास के किन तीन लोगों को आप रात्रिभोज पर आमंत्रित करना चाहेंगे और क्यों?", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "दैनिक जीवन की छोटी-छोटी खुशियों का जश्न मनाना क्यों जरूरी है?", category: "Impromptu Fun", difficulty: "Beginner" }
  ]
};

const TOPIC_ROULETTE_LIBRARY_ML = {
  technology: [
    { title: "നിർമ്മിത ബുദ്ധി (AI) വരും ദശകത്തിൽ തൊഴിൽ മേഖലയെ എങ്ങനെ മാറ്റിമറിക്കും?", category: "AI & Technology", difficulty: "Advanced" },
    { title: "സാങ്കേതികവിദ്യയുടെ വളർച്ച മനുഷ്യൻ്റെ സർഗ്ഗാത്മകതയെ എങ്ങനെ സ്വാധീനിക്കുന്നു?", category: "AI & Technology", difficulty: "Intermediate" },
    { title: "സൈബർ സുരക്ഷ ഇന്ന് നേരിടുന്ന ഏറ്റവും വലിയ വെല്ലുവിളികൾ എന്തൊക്കെയാണ്?", category: "AI & Technology", difficulty: "Advanced" },
    { title: "ക്ലൗഡ് കമ്പ്യൂട്ടിംഗും ആധുനിക സാങ്കേതികവിദ്യകളും എങ്ങനെ മാറ്റങ്ങൾ കൊണ്ടുവരുന്നു?", category: "AI & Technology", difficulty: "Intermediate" },
    { title: "വ്യക്തിഗത വിവര സംരക്ഷണവും സാങ്കേതികവിദ്യയും തമ്മിലുള്ള സന്തുലിതാവസ്ഥ.", category: "AI & Technology", difficulty: "Advanced" }
  ],
  science: [
    { title: "ഇരുപതാം നൂറ്റാണ്ടിലെയും ഇരുപത്തിയൊന്നാം നൂറ്റാണ്ടിലെയും ഏറ്റവും വലിയ ശാസ്ത്ര കണ്ടുപിടിത്തം ഏതാണ്?", category: "Science & Future", difficulty: "Intermediate" },
    { title: "കാലാവസ്ഥാ വ്യതിയാനം തടയാൻ ഹരിത ഊർജ്ജത്തിൻ്റെ പ്രാധാന്യം എന്താണ്?", category: "Science & Future", difficulty: "Intermediate" },
    { title: "ബഹിരാകാശ ഗവേഷണം മനുഷ്യരാശിയുടെ ഭാവിക്ക് എത്രത്തോളം ഗുണകരമാണ്?", category: "Science & Future", difficulty: "Advanced" },
    { title: "ശാസ്ത്ര ഗവേഷണവും സാങ്കേതികവിദ്യയും മനുഷ്യൻ്റെ ഭാവിക്ക് എത്രത്തോളം പ്രധാനമാണ്?", category: "Science & Future", difficulty: "Intermediate" },
    { title: "ക്വാണ്ടം കമ്പ്യൂട്ടിംഗ് ശാസ്ത്രലോകത്ത് എന്തെല്ലാം മാറ്റങ്ങൾ സൃഷ്ടിക്കും?", category: "Science & Future", difficulty: "Expert" }
  ],
  leadership: [
    { title: "പ്രതിസന്ധി ഘട്ടങ്ങളിൽ ഒരു ടീമിനെ എങ്ങനെ വിജയകരമായി നയിക്കാം?", category: "Executive Leadership", difficulty: "Advanced" },
    { title: "ഒരു നല്ല മാനേജറും മികച്ച ഭരണകർത്താവും തമ്മിലുള്ള പ്രധാന വ്യത്യാസങ്ങൾ എന്തൊക്കെയാണ്?", category: "Executive Leadership", difficulty: "Advanced" },
    { title: "തൊഴിലിടങ്ങളിൽ പരസ്പര വിശ്വാസവും സുരക്ഷിതത്വവും എങ്ങനെ വളർത്തിയെടുക്കാം?", category: "Executive Leadership", difficulty: "Intermediate" },
    { title: "വെല്ലുവിളികളെ ധൈര്യത്തോടെയും ആത്മവിശ്വാസത്തോടെയും എങ്ങനെ നേരിടാം?", category: "Executive Leadership", difficulty: "Expert" },
    { title: "വ്യക്തമായ ആശയവിനിമയം ഒരു ലീഡർക്ക് എത്രത്തോളം ആവശ്യമാണ്?", category: "Executive Leadership", difficulty: "Intermediate" }
  ],
  general: [
    { title: "നിങ്ങളുടെ ജീവിതത്തിലെ ഏറ്റവും വലിയ നേട്ടത്തെക്കുറിച്ചും അത് പഠിപ്പിച്ച പാഠങ്ങളെക്കുറിച്ചും സംസാരിക്കുക.", category: "Personal Growth", difficulty: "Intermediate" },
    { title: "പരാജയങ്ങളെ അതിജീവിച്ച് വിജയത്തിലെത്തിയ ഒരു അനുഭവത്തെക്കുറിച്ച് പറയുക.", category: "Personal Growth", difficulty: "Intermediate" },
    { title: "നിങ്ങളുടെ വീക്ഷണത്തിൽ യഥാർത്ഥ വിജയവും നേതൃത്വവും എന്താണ്?", category: "Personal Growth", difficulty: "Beginner" },
    { title: "ഔദ്യോഗിക ജീവിതവും വ്യക്തിജീവിതവും തമ്മിൽ എങ്ങനെ സന്തുലിതാവസ്ഥ നിലനിർത്താം?", category: "Personal Growth", difficulty: "Intermediate" },
    { title: "ജീവിതത്തിൽ നിരന്തരമായ പഠനത്തിൻ്റെയും സ്വയം നവീകരണത്തിൻ്റെയും പ്രാധാന്യം.", category: "Personal Growth", difficulty: "Beginner" }
  ],
  business: [
    { title: "വ്യാപാര സ്ഥാപനങ്ങൾ ലാഭത്തേക്കാൾ സാമൂഹിക പ്രതിബദ്ധതയ്ക്ക് മുൻഗണന നൽകണമോ?", category: "Business & Ethics", difficulty: "Advanced" },
    { title: "വീട്ടിലിരുന്നയുള്ള ജോലിയും (Remote Work) ഓഫീസ് സംസ്കാരവും തമ്മിലുള്ള മാറ്റങ്ങൾ.", category: "Business & Ethics", difficulty: "Intermediate" },
    { title: "ഉപഭോക്താക്കളുടെ വിശ്വാസ്യതയാണ് ഏതൊരു ബിസിനസ്സിൻ്റെയും ഏറ്റവും വലിയ മൂലധനം - എന്തുകൊണ്ട്?", category: "Business & Ethics", difficulty: "Intermediate" },
    { title: "ബിസിനസ്സ് രംഗത്ത് സത്യസന്ധതയും സുതാര്യതയും എത്രത്തോളം പ്രധാനമാണ്?", category: "Business & Ethics", difficulty: "Advanced" },
    { title: "പുതിയ സംരംഭങ്ങൾ (Startups) വ്യവസായ മേഖലയിൽ എന്തെല്ലാം മാറ്റങ്ങൾ കൊണ്ടുവരുന്നു?", category: "Business & Ethics", difficulty: "Intermediate" }
  ],
  fun: [
    { title: "നിങ്ങൾക്ക് ഭൂതകാലത്തിലേക്ക് യാത്ര ചെയ്യാൻ കഴിഞ്ഞാൽ ഏത് കാലഘട്ടത്തിലേക്ക് പോകും, എന്തുകൊണ്ട്?", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "രാവിലെ നേരത്തെ എഴുന്നേൽക്കുന്നത് വിജയത്തിൻ്റെ രഹസ്യമോ അതോ വെറും മിഥ്യയോ?", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "അന്യഗ്രഹജീവികളുമായി സംസാരിക്കാൻ അവസരം ലഭിച്ചാൽ നിങ്ങൾ ആദ്യം എന്ത് പറയും?", category: "Impromptu Fun", difficulty: "Intermediate" },
    { title: "ചരിത്രത്തിലെ ഏത് മൂന്ന് വ്യക്തികളെയാണ് നിങ്ങൾ ഒരു വിരുന്നിന് ക്ഷണിക്കാൻ ആഗ്രഹിക്കുന്നത്?", category: "Impromptu Fun", difficulty: "Beginner" },
    { title: "ജീവിതത്തിലെ കൊച്ചു കൊച്ചു സന്തോഷങ്ങൾ ആഘോഷിക്കേണ്ടതിൻ്റെ ആവശ്യകത.", category: "Impromptu Fun", difficulty: "Beginner" }
  ]
};

document.addEventListener("DOMContentLoaded", function () {
  const btnStart = document.getElementById("btnStartRecord");
  const btnStop = document.getElementById("btnStopRecord");
  const btnReset = document.getElementById("btnResetRecord");
  const btnSpinRoulette = document.getElementById("btnSpinRoulette");
  const btnAnalyze = document.getElementById("btnAnalyzeSpeech");
  const btnDemoText = document.getElementById("btnDemoText");

  if (btnStart) btnStart.addEventListener("click", startCountdownAndRecord);
  if (btnStop) btnStop.addEventListener("click", stopRecording);
  if (btnReset) btnReset.addEventListener("click", resetRecording);
  if (btnSpinRoulette) btnSpinRoulette.addEventListener("click", () => spinTopicRoulette(currentCategory));
  if (btnAnalyze) btnAnalyze.addEventListener("click", submitSpeechForAnalysis);
  if (btnDemoText) btnDemoText.addEventListener("click", populateDemoSpeech);

  // 0. Setup Language Selector Pills (English / Hindi / Malayalam)
  const langBtns = document.querySelectorAll(".lang-pill-btn");
  langBtns.forEach(btn => {
    btn.addEventListener("click", function () {
      langBtns.forEach(b => {
        b.classList.remove("btn-safe-space", "active");
        b.classList.add("btn-outline-safe");
      });
      this.classList.remove("btn-outline-safe");
      this.classList.add("btn-safe-space", "active");

      const lang = this.getAttribute("data-lang") || "en-US";
      window.selectedLanguage = lang;

      const langName = lang === "hi-IN" ? "हिंदी (Hindi)" : (lang === "ml-IN" ? "മലയാളം (Malayalam)" : "English");
      showToast(`Language switched to ${langName}. Topic Roulette & Speech Recognition updated!`, "info");

      const targetWpmText = document.getElementById("targetWpmText");
      if (targetWpmText) {
        if (lang === "hi-IN") {
          targetWpmText.textContent = "Target: 100–130 WPM";
        } else if (lang === "ml-IN") {
          targetWpmText.textContent = "Target: 80–110 WPM";
        } else {
          targetWpmText.textContent = "Target: 120–150 WPM";
        }
      }

      // Spin roulette in new language
      spinTopicRoulette(currentCategory);
    });
  });

  // 1. Setup Category Filter Pills
  const categoryBtns = document.querySelectorAll(".category-tab-btn");
  categoryBtns.forEach(btn => {
    btn.addEventListener("click", function () {
      categoryBtns.forEach(b => {
        b.classList.remove("btn-safe-space", "active");
        b.classList.add("btn-outline-safe");
      });
      this.classList.remove("btn-outline-safe");
      this.classList.add("btn-safe-space", "active");

      const category = this.getAttribute("data-category") || "all";
      currentCategory = category;
      spinTopicRoulette(category);
    });
  });

  // 1.5 Setup Difficulty Filter Pills
  const difficultyBtns = document.querySelectorAll(".difficulty-pill-btn");
  difficultyBtns.forEach(btn => {
    btn.addEventListener("click", function () {
      difficultyBtns.forEach(b => {
        b.classList.remove("btn-safe-space", "active");
        b.classList.add("btn-outline-safe");
      });
      this.classList.remove("btn-outline-safe");
      this.classList.add("btn-safe-space", "active");

      const difficulty = this.getAttribute("data-difficulty") || "Intermediate";
      currentDifficulty = difficulty;
      spinTopicRoulette(currentCategory);
    });
  });

  // 2. Setup Speech Duration Target Pills (30s, 60s, 120s)
  const durationBtns = document.querySelectorAll(".duration-pill-btn");
  durationBtns.forEach(btn => {
    btn.addEventListener("click", function () {
      durationBtns.forEach(b => {
        b.classList.remove("btn-safe-space", "active");
        b.classList.add("btn-outline-safe");
      });
      this.classList.remove("btn-outline-safe");
      this.classList.add("btn-safe-space", "active");

      const durationSecs = parseInt(this.getAttribute("data-duration") || "60", 10);
      window.selectedDurationSeconds = durationSecs;
      updateTimerDisplay(elapsedSeconds);
      showToast(`Target duration set to ${formatDurationLabel(durationSecs)}`, "info");
    });
  });

  // Initialize Canvas background
  initEmptyWaveCanvas();
  updateTimerDisplay(0);
});

function formatDurationLabel(seconds) {
  if (seconds === 30) return "30 Seconds";
  if (seconds === 60) return "1 Minute";
  if (seconds === 120) return "2 Minutes";
  return `${seconds}s`;
}

/**
 * WEB AUDIO API SYNTHESIZER FOR ROULETTE SOUND EFFECTS
 * Generates high-end mechanical wheel ticks and celebration chimes without external audio files
 */
let soundEffectsCtx = null;

function getSoundEffectsContext() {
  try {
    if (!soundEffectsCtx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        soundEffectsCtx = new AudioCtx();
      }
    }
    if (soundEffectsCtx && soundEffectsCtx.state === "suspended") {
      soundEffectsCtx.resume();
    }
    return soundEffectsCtx;
  } catch (e) {
    return null;
  }
}

/**
 * Plays a crisp mechanical roulette peg "tick" / "click" sound
 */
function playRouletteTickSound() {
  try {
    const ctx = getSoundEffectsContext();
    if (!ctx) return;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    // Crisp triangle wave with slight pitch variation for mechanical feel
    osc.type = "triangle";
    osc.frequency.setValueAtTime(860 + Math.random() * 140, ctx.currentTime);

    // Very fast decay envelope (click/tick effect)
    gain.gain.setValueAtTime(0.14, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.035);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start();
    osc.stop(ctx.currentTime + 0.035);
  } catch (e) {
    // Ignore if browser blocks audio before user interaction
  }
}

/**
 * Plays an uplifting 3-note major triad celebration bell chime when the wheel lands on a topic
 */
function playRouletteWinSound() {
  try {
    const ctx = getSoundEffectsContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    // C5 (523.25 Hz), E5 (659.25 Hz), G5 (783.99 Hz)
    const notes = [523.25, 659.25, 783.99];

    notes.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, now + idx * 0.065);

      gain.gain.setValueAtTime(0.0, now + idx * 0.065);
      gain.gain.linearRampToValueAtTime(0.16, now + idx * 0.065 + 0.018);
      gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.065 + 0.45);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now + idx * 0.065);
      osc.stop(now + idx * 0.065 + 0.48);
    });
  } catch (e) {
    // Ignore if browser blocks audio before user interaction
  }
}

/**
 * 1. TOPIC ROULETTE / SLOT-MACHINE WHEEL PICKER EFFECT
 * Rapidly cycles through subtopics with a decelerating slot animation & sound effects
 */
function spinTopicRoulette(category = "all") {
  if (isRouletteSpinning) return;
  isRouletteSpinning = true;

  const topicTitleEl = document.getElementById("topicTitle");
  const topicCategoryEl = document.getElementById("topicCategoryBadge");
  const topicDifficultyEl = document.getElementById("topicDifficultyBadge");
  const rouletteBox = document.getElementById("rouletteBox");
  const btnSpin = document.getElementById("btnSpinRoulette");

  if (btnSpin) {
    btnSpin.disabled = true;
    btnSpin.innerHTML = `<i class="bi bi-arrow-repeat animate-spin me-2"></i> Spinning Roulette...`;
  }

  // Gather available subtopics based on selected language (English, Hindi, or Malayalam)
  const activeLibrary = window.selectedLanguage === "hi-IN"
    ? TOPIC_ROULETTE_LIBRARY_HI
    : (window.selectedLanguage === "ml-IN" ? TOPIC_ROULETTE_LIBRARY_ML : TOPIC_ROULETTE_LIBRARY);

  let available = [];
  if (category === "all") {
    Object.values(activeLibrary).forEach(arr => available.push(...arr));
  } else {
    available = activeLibrary[category] || activeLibrary.general;
  }

  // Filter by difficulty
  let filteredByDifficulty = available.filter(t => t.difficulty === currentDifficulty);
  if (filteredByDifficulty.length > 0) {
    available = filteredByDifficulty;
  }

  // Pick the winning final topic
  const winningIndex = Math.floor(Math.random() * available.length);
  const winningTopic = available[winningIndex];

  // Easing intervals for mechanical roulette wheel feel
  const intervals = [40, 50, 60, 75, 95, 120, 155, 200, 260, 340, 450, 600];
  let step = 0;

  if (rouletteBox) {
    rouletteBox.style.borderColor = "#2E4637";
    rouletteBox.style.backgroundColor = "#EBF1ED";
  }
  if (topicTitleEl) {
    topicTitleEl.style.transform = "scale(0.97)";
    topicTitleEl.style.opacity = "0.75";
  }

  function doNextSpinStep() {
    if (step < intervals.length) {
      // Play mechanical roulette tick sound effect
      playRouletteTickSound();

      // Pick a temporary random topic while wheel is spinning
      const tempItem = available[Math.floor(Math.random() * available.length)];
      if (topicTitleEl) topicTitleEl.textContent = tempItem.title;
      if (topicCategoryEl) topicCategoryEl.textContent = tempItem.category;
      if (topicDifficultyEl) topicDifficultyEl.textContent = tempItem.difficulty;

      const delay = intervals[step];
      step++;
      setTimeout(doNextSpinStep, delay);
    } else {
      // Land on winning topic & play winning chime sound effect!
      playRouletteWinSound();

      isRouletteSpinning = false;
      currentTopicTitle = winningTopic.title;
      if (topicTitleEl) {
        topicTitleEl.textContent = winningTopic.title;
        topicTitleEl.style.transform = "scale(1.02)";
        topicTitleEl.style.opacity = "1";
        setTimeout(() => {
          topicTitleEl.style.transform = "scale(1)";
        }, 200);
      }
      if (topicCategoryEl) topicCategoryEl.textContent = winningTopic.category;
      if (topicDifficultyEl) topicDifficultyEl.textContent = winningTopic.difficulty;
      if (rouletteBox) {
        rouletteBox.style.backgroundColor = "#FBF9F5";
        rouletteBox.style.borderColor = "#D3CDC4";
      }
      if (btnSpin) {
        btnSpin.disabled = false;
        btnSpin.innerHTML = `<i class="bi bi-dice-5-fill me-2"></i> Spin Topic Roulette 🎲`;
      }
      showToast("🎲 Topic selected via Roulette!", "success");
    }
  }

  doNextSpinStep();
}

/**
 * 2. Countdown Timer before Starting Recording (3 - 2 - 1 - GO!)
 */
function startCountdownAndRecord() {
  const countdownOverlay = document.getElementById("countdownOverlay");
  const countdownNumber = document.getElementById("countdownNumber");
  const btnStart = document.getElementById("btnStartRecord");

  if (btnStart) btnStart.disabled = true;

  if (countdownOverlay && countdownNumber) {
    countdownOverlay.classList.remove("d-none");
    let count = 3;
    countdownNumber.textContent = count;

    const countInterval = setInterval(() => {
      count--;
      if (count > 0) {
        countdownNumber.textContent = count;
      } else if (count === 0) {
        countdownNumber.textContent = "GO!";
      } else {
        clearInterval(countInterval);
        countdownOverlay.classList.add("d-none");
        beginMicrophoneRecording();
      }
    }, 1000);
  } else {
    beginMicrophoneRecording();
  }
}

/**
 * 3. Begin Microphone Recording & Real-time Web Speech API Transcription
 */
async function beginMicrophoneRecording() {
  const btnStart = document.getElementById("btnStartRecord");
  const btnStop = document.getElementById("btnStopRecord");
  const btnReset = document.getElementById("btnResetRecord");
  const micStatus = document.getElementById("micStatusText");

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyserNode = audioContext.createAnalyser();
    analyserNode.fftSize = 256;

    const sourceNode = audioContext.createMediaStreamSource(stream);
    sourceNode.connect(analyserNode);

    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream, { mimeType: getSupportedMimeType() });

    mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        audioChunks.push(e.data);
      }
    };

    mediaRecorder.onstop = () => {
      audioBlob = new Blob(audioChunks, { type: getSupportedMimeType() });
      stream.getTracks().forEach(track => track.stop());
    };

    mediaRecorder.start(250);
    isRecording = true;

    // Start UI updates
    elapsedSeconds = 0;
    updateTimerDisplay(0);
    startSpeechTimer();
    visualizeWaveform();
    startAcousticTelemetryTracker();

    // Start Web Speech API Transcription
    setupSpeechRecognition();

    // Start Visual Presence Recording automatically
    if (!webcamAnalyzer && window.WebcamAnalyzer && document.getElementById('webcamPreview')) {
      const btnEnableCamera = document.getElementById('btnEnableCamera');
      if (btnEnableCamera) {
        btnEnableCamera.disabled = true;
        btnEnableCamera.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Starting Camera...';
      }
      try {
        webcamAnalyzer = new window.WebcamAnalyzer(
          document.getElementById('webcamPreview'),
          document.getElementById('webcamIndicator')
        );
        await webcamAnalyzer.initialize();
        if (btnEnableCamera) {
          btnEnableCamera.innerHTML = '<i class="bi bi-check-circle-fill text-success"></i> Camera Active';
        }
      } catch (err) {
        console.error("Auto camera init failed:", err);
        if (btnEnableCamera) {
          btnEnableCamera.innerHTML = '<i class="bi bi-exclamation-triangle-fill text-danger"></i> Failed';
        }
      }
    }
    
    if (webcamAnalyzer) {
      webcamAnalyzer.startRecording();
    }

    if (btnStart) btnStart.classList.add("d-none");
    if (btnStop) {
      btnStop.classList.remove("d-none");
      btnStop.classList.add("btn-record-active");
    }
    if (btnReset) btnReset.disabled = false;
    if (micStatus) {
      const targetDurationStr = formatDurationLabel(window.selectedDurationSeconds || 60);
      micStatus.innerHTML = `<span class="text-danger fw-bold"><i class="bi bi-record-circle me-1 animate-pulse"></i> RECORDING LIVE</span> — Target Duration: ${targetDurationStr}. Speak clearly into your mic...`;
    }

  } catch (err) {
    console.error("Microphone access error:", err);
    showToast("Microphone access denied or unavailable. You can still type in the transcript box below.", "error");
    if (btnStart) btnStart.disabled = false;
  }
}

function getSupportedMimeType() {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4"
  ];
  for (const t of types) {
    if (MediaRecorder.isTypeSupported(t)) return t;
  }
  return "";
}

/**
 * 4. Stop Recording
 */
function stopRecording() {
  const btnStart = document.getElementById("btnStartRecord");
  const btnStop = document.getElementById("btnStopRecord");
  const micStatus = document.getElementById("micStatusText");

  isRecording = false;
  stopSpeechTimer();
  stopAcousticTelemetryTracker();

  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
  if (recognition) {
    try { recognition.stop(); } catch(e) {}
  }
  if (audioContext) {
    try { audioContext.close(); } catch(e) {}
  }
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }
  
  if (webcamAnalyzer) {
    const metrics = webcamAnalyzer.stopRecording();
    if (metrics) {
      visualMetricsData = metrics;
    }
  }

  if (btnStop) {
    btnStop.classList.add("d-none");
    btnStop.classList.remove("btn-record-active");
  }
  if (btnStart) {
    btnStart.classList.remove("d-none");
    btnStart.disabled = false;
    btnStart.textContent = "Resume / Re-record";
  }
  if (micStatus) {
    micStatus.innerHTML = `<i class="bi bi-check-circle-fill text-success me-1"></i> Recording stopped. You can review or edit the transcript below before AI evaluation.`;
  }

  initEmptyWaveCanvas();
}

/**
 * 5. Reset Recording Studio
 */
function resetRecording() {
  stopRecording();
  elapsedSeconds = 0;
  updateTimerDisplay(0);
  resetAcousticTelemetryDisplay();
  audioBlob = null;
  audioChunks = [];
  visualMetricsData = null;
  const transcriptBox = document.getElementById("transcriptTextarea");
  if (transcriptBox) {
    transcriptBox.value = "";
    transcriptBox.innerHTML = "";
  }
  const btnStart = document.getElementById("btnStartRecord");
  if (btnStart) btnStart.textContent = "Start Recording";
  showToast("Speech practice studio reset.", "info");
}

/**
 * 6. Setup Speech-to-Text Recognition (Web Speech API)
 */
function setupSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("Web Speech API not supported in this browser. Please use Google Chrome or Microsoft Edge.");
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = window.selectedLanguage || "en-US";

  const transcriptBox = document.getElementById("transcriptTextarea");
  let finalTranscript = transcriptBox ? (transcriptBox.value || transcriptBox.innerText || "") : "";

  function highlightErrors(text) {
    const fillers = ["um", "uh", "like", "you know", "literally", "basically", "so yeah"];
    
    // Basic grammar rules matching the backend NLP fallback
    const grammarRules = [
      { regex: /\b(how come|how comes)\b/gi, msg: "Informal syntax: use 'Why'" },
      { regex: /\b(can able to|could able to)\b/gi, msg: "Redundant phrasing: use 'can' or 'able to'" },
      { regex: /\b(will going to)\b/gi, msg: "Redundant future phrasing: use 'will' or 'going to'" },
      { regex: /\b(discuss about)\b/gi, msg: "'Discuss' does not need 'about'" },
      { regex: /\b(return back|revert back|reply back)\b/gi, msg: "Redundant 'back'" },
      { regex: /\b(repeat again)\b/gi, msg: "Redundant 'again'" },
      { regex: /\b(more better|more easier|more faster|most best)\b/gi, msg: "Avoid double comparative/superlative" },
      { regex: /\b(did not|didn't)\s+(went|saw|knew|said|came|made|took|gave)\b/gi, msg: "Use base verb after 'did not'" },
      { regex: /\b(he|she|it)\s+(go|do|have|know|make|take|say|want|need)\b/gi, msg: "Subject-verb agreement: use 3rd person singular verb" },
      { regex: /\b(they|we|you|people)\s+(is|was|has)\b/gi, msg: "Subject-verb agreement: use plural verb" },
    ];

    let highlighted = text;
    let hasError = false;

    // 1. Highlight grammar mistakes with a red wavy underline and tooltip
    grammarRules.forEach(rule => {
      if (rule.regex.test(highlighted)) hasError = true;
      highlighted = highlighted.replace(rule.regex, `<span class="highlight-grammar text-danger fw-bold" style="text-decoration: underline wavy #ff4d4f 2px; cursor: help;" title="Grammar Correction: $& -> ${rule.msg}">$&</span>`);
    });

    // 2. Highlight fillers with a warning badge
    fillers.forEach(f => {
      const regex = new RegExp(`\\b${f}\\b`, 'gi');
      if (regex.test(highlighted)) hasError = true;
      highlighted = highlighted.replace(regex, `<span class="highlight-filler badge bg-warning-subtle text-warning border border-warning px-2 py-1 mx-1" title="Filler word detected">$&</span>`);
    });

    // Haptic feedback (Smartwatch / Apple Watch / Mobile)
    if (hasError && navigator.vibrate) {
      navigator.vibrate([100, 50, 100]);
    }
    return highlighted;
  }

  recognition.onresult = (event) => {
    let interimTranscript = "";
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        finalTranscript += event.results[i][0].transcript + " ";
      } else {
        interimTranscript += event.results[i][0].transcript;
      }
    }
    if (transcriptBox) {
      let combined = (finalTranscript + interimTranscript).trim();
      if (transcriptBox.tagName.toLowerCase() === "textarea") {
        transcriptBox.value = combined;
      } else {
        transcriptBox.innerHTML = highlightErrors(combined);
        // Teleprompter Auto-Scroll
        transcriptBox.scrollTop = transcriptBox.scrollHeight;
      }
    }
  };

  recognition.onerror = (event) => {
    console.warn("Speech recognition error:", event.error);
  };

  recognition.onend = () => {
    // Restart recognition automatically if still recording
    if (isRecording) {
      try { recognition.start(); } catch(e) {}
    }
  };

  try {
    recognition.start();
  } catch(e) {}
}

/**
 * 7. Live HTML5 Canvas Waveform Visualization
 */
function visualizeWaveform() {
  if (!isRecording || !analyserNode) return;

  const canvas = document.getElementById("waveCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  const bufferLength = analyserNode.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  function draw() {
    if (!isRecording) return;
    animationFrameId = requestAnimationFrame(draw);

    analyserNode.getByteTimeDomainData(dataArray);

    ctx.fillStyle = "#FBF9F5";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.lineWidth = 2.5;
    ctx.strokeStyle = "#2E4637";
    ctx.beginPath();

    const sliceWidth = canvas.width * 1.0 / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const v = dataArray[i] / 128.0;
      const y = (v * canvas.height) / 2;

      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
      x += sliceWidth;
    }

    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();
  }

  draw();
}

function initEmptyWaveCanvas() {
  const canvas = document.getElementById("waveCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#FBF9F5";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Draw static reference wave line
  ctx.strokeStyle = "rgba(46, 70, 55, 0.35)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, canvas.height / 2);
  ctx.lineTo(canvas.width, canvas.height / 2);
  ctx.stroke();
}

/**
 * 8. Speech Timer Helpers
 */
function startSpeechTimer() {
  stopSpeechTimer();
  speechTimerInterval = setInterval(() => {
    elapsedSeconds++;
    updateTimerDisplay(elapsedSeconds);
  }, 1000);
}

function stopSpeechTimer() {
  if (speechTimerInterval) clearInterval(speechTimerInterval);
}

function updateTimerDisplay(seconds) {
  const timerEl = document.getElementById("speechTimerDisplay");
  if (!timerEl) return;
  const mins = Math.floor(seconds / 60).toString().padStart(2, "0");
  const secs = (seconds % 60).toString().padStart(2, "0");

  const targetTotal = window.selectedDurationSeconds || 60;
  const targetMins = Math.floor(targetTotal / 60).toString().padStart(2, "0");
  const targetSecs = (targetTotal % 60).toString().padStart(2, "0");

  timerEl.textContent = `${mins}:${secs} / ${targetMins}:${targetSecs}`;
}

/**
 * 8B. Live Acoustic Telemetry & Pause Ratio Intelligence Analyzer
 */
function startAcousticTelemetryTracker() {
  stopAcousticTelemetryTracker();
  isCurrentlyPaused = false;
  pauseStartTime = 0;
  dramaticPausesCount = 0;
  hesitationPausesCount = 0;
  totalSpeakingSeconds = 0;
  totalPauseSeconds = 0;

  const wpmBadge = document.getElementById("wpmStatusBadge");
  const pauseBadge = document.getElementById("pauseStatusBadge");
  if (wpmBadge) {
    wpmBadge.textContent = "🟢 Live Recording Active";
    wpmBadge.style.backgroundColor = "#EBF1ED";
    wpmBadge.style.color = "#2E4637";
    wpmBadge.style.borderColor = "#D2DFD6";
  }
  if (pauseBadge) {
    pauseBadge.textContent = "🎙️ Analyzing Pauses...";
    pauseBadge.style.backgroundColor = "#EBF1ED";
    pauseBadge.style.color = "#2E4637";
    pauseBadge.style.borderColor = "#D2DFD6";
  }

  pauseTrackerInterval = setInterval(() => {
    if (!isRecording) return;

    // 1. Update WPM Speedometer Gauge
    updateWpmSpeedometerGauge();

    // 2. Check Acoustic Silence Level via AnalyserNode
    if (!analyserNode) return;
    const bufferLength = analyserNode.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    analyserNode.getByteTimeDomainData(dataArray);

    let sum = 0;
    for (let i = 0; i < bufferLength; i++) {
      const norm = (dataArray[i] - 128) / 128.0;
      sum += norm * norm;
    }
    const rms = Math.sqrt(sum / bufferLength);

    // Threshold for silence/pause detection
    const isSilent = rms < 0.012;
    if (isSilent) {
      totalPauseSeconds += 0.25;
      if (!isCurrentlyPaused) {
        isCurrentlyPaused = true;
        pauseStartTime = Date.now();
      }
    } else {
      totalSpeakingSeconds += 0.25;
      if (isCurrentlyPaused) {
        const pauseDuration = (Date.now() - pauseStartTime) / 1000;
        isCurrentlyPaused = false;

        // Classify completed pause (1.0s or longer)
        if (pauseDuration >= 1.0) {
          const textEl = document.getElementById("transcriptTextarea");
          const text = textEl ? textEl.value.trim() : "";
          const isSentenceEnd = /[.!?;:]$/.test(text);

          if (pauseDuration <= 2.5 && isSentenceEnd) {
            dramaticPausesCount++;
            const el = document.getElementById("dramaticPausesCount");
            if (el) el.textContent = dramaticPausesCount;

            if (pauseBadge) {
              pauseBadge.innerHTML = `✨ Dramatic Pause Detected (+1)`;
              pauseBadge.style.backgroundColor = "#E8F5E9";
              pauseBadge.style.color = "#2E7D32";
              pauseBadge.style.borderColor = "#A5D6A7";
            }
          } else {
            hesitationPausesCount++;
            const el = document.getElementById("hesitationPausesCount");
            if (el) el.textContent = hesitationPausesCount;

            if (pauseBadge) {
              pauseBadge.innerHTML = `⚠️ Hesitation Pause Detected (+1)`;
              pauseBadge.style.backgroundColor = "#FFF8E1";
              pauseBadge.style.color = "#E65100";
              pauseBadge.style.borderColor = "#FFE082";
            }
          }
        }
      }
    }

    // 3. Update Pause Ratio Display
    updatePauseRatioDisplay();
  }, 250);
}

function stopAcousticTelemetryTracker() {
  if (pauseTrackerInterval) {
    clearInterval(pauseTrackerInterval);
    pauseTrackerInterval = null;
  }
}

function resetAcousticTelemetryDisplay() {
  stopAcousticTelemetryTracker();
  liveWpm = 0;
  dramaticPausesCount = 0;
  hesitationPausesCount = 0;
  totalSpeakingSeconds = 0;
  totalPauseSeconds = 0;
  isCurrentlyPaused = false;

  const wpmEl = document.getElementById("liveWpmDisplay");
  if (wpmEl) wpmEl.textContent = "0";
  const wpmBar = document.getElementById("wpmGaugeBar");
  if (wpmBar) {
    wpmBar.style.width = "0%";
    wpmBar.style.backgroundColor = "#2E4637";
  }
  const wpmBadge = document.getElementById("wpmStatusBadge");
  if (wpmBadge) {
    wpmBadge.textContent = "Waiting for Speech...";
    wpmBadge.style.backgroundColor = "#EBF1ED";
    wpmBadge.style.color = "#2E4637";
    wpmBadge.style.borderColor = "#D2DFD6";
  }

  const dramEl = document.getElementById("dramaticPausesCount");
  if (dramEl) dramEl.textContent = "0";
  const hesEl = document.getElementById("hesitationPausesCount");
  if (hesEl) hesEl.textContent = "0";
  const ratioEl = document.getElementById("pauseRatioDisplay");
  if (ratioEl) ratioEl.textContent = "0%";

  const pauseBadge = document.getElementById("pauseStatusBadge");
  if (pauseBadge) {
    pauseBadge.textContent = "Pause Tracker Ready";
    pauseBadge.style.backgroundColor = "#F4EFEA";
    pauseBadge.style.color = "#6A665E";
    pauseBadge.style.borderColor = "#DFDAD2";
  }
}

function updateWpmSpeedometerGauge() {
  const textEl = document.getElementById("transcriptTextarea");
  const text = textEl ? (textEl.value || textEl.innerText || "").trim() : "";
  const words = text ? text.split(/\s+/).filter(Boolean).length : 0;

  if (elapsedSeconds >= 2 && words > 0) {
    liveWpm = Math.round((words / elapsedSeconds) * 60);
  } else {
    liveWpm = 0;
  }

  const wpmEl = document.getElementById("liveWpmDisplay");
  if (wpmEl) wpmEl.textContent = liveWpm;

  const wpmBar = document.getElementById("wpmGaugeBar");
  if (wpmBar) {
    const widthPct = Math.min(100, Math.round((liveWpm / 250) * 100));
    wpmBar.style.width = `${widthPct}%`;
  }

  const wpmBadge = document.getElementById("wpmStatusBadge");
  if (!wpmBadge) return;

  if (words === 0 || elapsedSeconds < 3) {
    wpmBadge.textContent = "🎙️ Waiting for Speech...";
    wpmBadge.style.backgroundColor = "#EBF1ED";
    wpmBadge.style.color = "#2E4637";
    wpmBadge.style.borderColor = "#D2DFD6";
    if (wpmBar) wpmBar.style.backgroundColor = "#2E4637";
  } else if (liveWpm >= 120 && liveWpm <= 150) {
    wpmBadge.textContent = `🟢 Optimal Executive Pacing (${liveWpm} WPM)`;
    wpmBadge.style.backgroundColor = "#2E7D32";
    wpmBadge.style.color = "#FFFFFF";
    wpmBadge.style.borderColor = "#1B5E20";
    if (wpmBar) wpmBar.style.backgroundColor = "#2E7D32";
  } else if ((liveWpm >= 90 && liveWpm < 120) || (liveWpm > 150 && liveWpm <= 170)) {
    const label = liveWpm < 120 ? `🟡 Slightly Slow (${liveWpm} WPM)` : `🟡 Slightly Fast (${liveWpm} WPM)`;
    wpmBadge.textContent = label;
    wpmBadge.style.backgroundColor = "#FFC107";
    wpmBadge.style.color = "#1C1B18";
    wpmBadge.style.borderColor = "#FFA000";
    if (wpmBar) wpmBar.style.backgroundColor = "#FFC107";
  } else {
    const label = liveWpm < 90 ? `🔴 Too Slow / Hesitant (< 90 WPM)` : `🔴 Too Fast / Rushed (> 170 WPM)`;
    wpmBadge.textContent = label;
    wpmBadge.style.backgroundColor = "#DC3545";
    wpmBadge.style.color = "#FFFFFF";
    wpmBadge.style.borderColor = "#B02A37";
    if (wpmBar) wpmBar.style.backgroundColor = "#DC3545";

    // Sustained Pacing Haptic Warning (long pulse)
    if (elapsedSeconds > 5 && Math.random() < 0.25 && navigator.vibrate) {
      navigator.vibrate(200);
    }
  }
}

function updatePauseRatioDisplay() {
  const ratioEl = document.getElementById("pauseRatioDisplay");
  if (!ratioEl) return;
  const totalTime = totalSpeakingSeconds + totalPauseSeconds;
  const ratio = totalTime > 0 ? Math.round((totalPauseSeconds / totalTime) * 100) : 0;
  ratioEl.textContent = `${ratio}%`;
}

/**
 * 9. Populate Demo Speech (for instant testing without speaking in English, Hindi, or Malayalam)
 */
function populateDemoSpeech() {
  let demoText = "Um hello everyone, this is like literally a test of filler words and executive presence. When we examine the future of artificial intelligence, we must recognize both its incredible potential and its ethical challenges. I believe that true leadership requires transparent communication, continuous learning, and empathy. Thank you for your attention.";
  
  if (window.selectedLanguage === "hi-IN") {
    demoText = "नमस्ते सभी को, यह सार्वजनिक भाषण और नेतृत्व कौशल का एक अभ्यास है। जब हम आर्टिफिशियल इंटेलिजेंस के भविष्य को देखते हैं, तो हमें इसकी अपार संभावनाओं और नैतिक चुनौतियों दोनों को समझना होगा। मैं मानता हूँ कि सच्चे नेतृत्व के लिए स्पष्ट संवाद, सतत सीखना और सहानुभूति आवश्यक है। धन्यवाद।";
  } else if (window.selectedLanguage === "ml-IN") {
    demoText = "എല്ലാവർക്കും നമസ്കാരം, ഇത് പൊതുപ്രസംഗത്തിൻ്റെയും നേതൃത്വ പാടവത്തിൻ്റെയും ഒരു പരിശീലനമാണ്. നിർമ്മിത ബുദ്ധിയുടെ ഭാവി പരിശോധിക്കുമ്പോൾ അതിൻ്റെ വലിയ സാധ്യതകളും ധാർമ്മിക വെല്ലുവിളികളും നാം മനസ്സിലാക്കേണ്ടതുണ്ട്. മികച്ച നേതൃത്വത്തിന് വ്യക്തമായ ആശയവിനിമയവും സഹാനുഭൂതിയും അത്യന്താപേക്ഷിതമാണെന്ന് ഞാൻ വിശ്വസിക്കുന്നു. നന്ദി.";
  }

  const transcriptBox = document.getElementById("transcriptTextarea");
  if (transcriptBox) {
    if (transcriptBox.tagName.toLowerCase() === "textarea") {
      transcriptBox.value = demoText;
    } else {
      transcriptBox.innerHTML = demoText;
    }
    if (window.triggerAudienceSmileEffect) window.triggerAudienceSmileEffect(true);
    showToast("Demo speech loaded! Audience is smiling & engaged!", "success");
  }

  // Populate Demo Telemetry Metrics so user can instantly preview speedometer & pause analyzer
  liveWpm = 138;
  dramaticPausesCount = 4;
  hesitationPausesCount = 1;
  totalSpeakingSeconds = 48;
  totalPauseSeconds = 12;

  const wpmEl = document.getElementById("liveWpmDisplay");
  if (wpmEl) wpmEl.textContent = "138";
  const wpmBar = document.getElementById("wpmGaugeBar");
  if (wpmBar) {
    wpmBar.style.width = "55%";
    wpmBar.style.backgroundColor = "#2E7D32";
  }
  const wpmBadge = document.getElementById("wpmStatusBadge");
  if (wpmBadge) {
    wpmBadge.textContent = "🟢 Optimal Executive Pacing (138 WPM)";
    wpmBadge.style.backgroundColor = "#2E7D32";
    wpmBadge.style.color = "#FFFFFF";
    wpmBadge.style.borderColor = "#1B5E20";
  }
  const dramEl = document.getElementById("dramaticPausesCount");
  if (dramEl) dramEl.textContent = "4";
  const hesEl = document.getElementById("hesitationPausesCount");
  if (hesEl) hesEl.textContent = "1";
  const ratioEl = document.getElementById("pauseRatioDisplay");
  if (ratioEl) ratioEl.textContent = "20%";

  const pauseBadge = document.getElementById("pauseStatusBadge");
  if (pauseBadge) {
    pauseBadge.innerHTML = "✨ 4 Dramatic Pauses • Optimal Ratio (20%)";
    pauseBadge.style.backgroundColor = "#E8F5E9";
    pauseBadge.style.color = "#2E7D32";
    pauseBadge.style.borderColor = "#A5D6A7";
  }
}

/**
 * 10. Submit Speech for Google Gemini AI Evaluation
 */
async function submitSpeechForAnalysis() {
  const transcriptBox = document.getElementById("transcriptTextarea");
  let transcript = "";
  if (transcriptBox) {
    if (transcriptBox.tagName.toLowerCase() === "textarea") {
      transcript = (transcriptBox.value || "").trim();
    } else {
      transcript = (transcriptBox.innerText || transcriptBox.textContent || "").trim();
    }
  }

  if (!transcript) {
    showToast("Please speak into your microphone or type a speech transcript before analyzing.", "error");
    return;
  }

  // Show loading modal/spinner
  const loadingModalEl = document.getElementById("aiLoadingModal");
  let loadingModal = null;
  if (loadingModalEl) {
    loadingModal = new bootstrap.Modal(loadingModalEl, { backdrop: "static", keyboard: false });
    loadingModal.show();
  }

  const formData = new FormData();
  formData.append("transcript", transcript);
  if (currentTopicId) formData.append("topic_id", currentTopicId);
  formData.append("topic_title", currentTopicTitle || "General Practice");
  formData.append("duration_seconds", window.selectedDurationSeconds || maxTime(elapsedSeconds, 60));
  formData.append("language", window.selectedLanguage || "en-US");
  if (audioBlob) {
    formData.append("audio_file", audioBlob, "speech_recording.webm");
  }
  if (visualMetricsData) {
    formData.append("visual_metrics", JSON.stringify(visualMetricsData));
  }

  try {
    const response = await fetch("/api/speech/analyze/", {
      method: "POST",
      body: formData,
      headers: {
        "X-CSRFToken": getCsrfToken()
      }
    });

    const data = await response.json();
    if (data.status === "success" && data.redirect_url) {
      window.location.href = data.redirect_url;
    } else {
      if (loadingModal) loadingModal.hide();
      showToast(data.message || "Error analyzing speech.", "error");
    }
  } catch (err) {
    if (loadingModal) loadingModal.hide();
    console.error("AJAX Error:", err);
    showToast("Failed to connect to AI server.", "error");
  }
}

function maxTime(val, defaultVal) {
  return val > 5 ? val : defaultVal;
}

function getCsrfToken() {
  const name = "csrftoken";
  let cookieValue = null;
  if (document.cookie && document.cookie !== "") {
    const cookies = document.cookie.split(";");
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + "=")) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue || "";
}

/**
 * Toast Alert Helper
 */
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const bgClass = type === "error" ? "bg-danger text-white" : type === "success" ? "bg-success text-white" : "bg-dark text-white";
  const icon = type === "error" ? "bi-exclamation-triangle-fill" : type === "success" ? "bi-check-circle-fill" : "bi-info-circle-fill";

  const toastEl = document.createElement("div");
  toastEl.className = `toast align-items-center border-0 shadow-lg ${bgClass} rounded-4`;
  toastEl.setAttribute("role", "alert");
  toastEl.setAttribute("aria-live", "assertive");
  toastEl.setAttribute("aria-atomic", "true");

  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body d-flex align-items-center gap-2">
        <i class="bi ${icon} fs-5"></i>
        <span>${message}</span>
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  container.appendChild(toastEl);
  const bsToast = new bootstrap.Toast(toastEl, { delay: 4000 });
  bsToast.show();

  toastEl.addEventListener("hidden.bs.toast", () => {
    toastEl.remove();
  });
}

/**
 * --- INTERACTIVE AI SPEAKING STAGE & AUDIENCE OVERLAY EFFECT ---
 * Inspired by Framer interactive image overlays:
 * Hover over John (Speaker), Devi (Coach), or Mike (Audience) to fade in their overlay image.
 * When speaking well (score >= 75 or clicking 'Trigger Smile Effect'), the audience smiles and celebrates!
 */
document.addEventListener("DOMContentLoaded", () => {
  const overlayJohn = document.getElementById("overlayJohn");
  const overlayDevi = document.getElementById("overlayDevi");
  const overlayMike = document.getElementById("overlayMike");
  const stageTooltip = document.getElementById("stageTooltip");
  const stageTooltipText = document.getElementById("stageTooltipText");
  const stageMoodBadge = document.getElementById("stageMoodBadge");
  const btnToggleSmileEffect = document.getElementById("btnToggleSmileEffect");
  const stageZones = document.querySelectorAll(".stage-zone");

  let isSmilingMode = false;

  const tooltipMessages = {
    John: "John (AI Speaker): Delivering with 100% posture, steady eye contact, and vocal clarity!",
    Devi: "Devi (AI Evaluator): Listening for pacing, grammatical accuracy, and effective pauses.",
    Mike: "Mike (Audience): Highly attentive and ready to applaud a well-structured speech!",
  };

  // Hover effect over each character zone
  stageZones.forEach((zone) => {
    zone.addEventListener("mouseenter", () => {
      const target = zone.getAttribute("data-target");
      if (stageTooltip && stageTooltipText) {
        stageTooltipText.textContent = tooltipMessages[target] || "Hover over any person to interact!";
        stageTooltip.classList.remove("d-none");
      }
      if (!isSmilingMode) {
        if (target === "John" && overlayJohn) {
          overlayJohn.style.opacity = "1";
          overlayJohn.style.transform = "scale(0.53)";
        }
        if (target === "Devi" && overlayDevi) {
          overlayDevi.style.opacity = "1";
          overlayDevi.style.transform = "scale(0.60)";
        }
        if (target === "Mike" && overlayMike) {
          overlayMike.style.opacity = "1";
          overlayMike.style.transform = "scale(0.64)";
        }
      }
    });

    zone.addEventListener("mouseleave", () => {
      const target = zone.getAttribute("data-target");
      if (stageTooltip) stageTooltip.classList.add("d-none");
      if (!isSmilingMode) {
        if (target === "John" && overlayJohn) {
          overlayJohn.style.opacity = "0";
          overlayJohn.style.transform = "scale(0.50)";
        }
        if (target === "Devi" && overlayDevi) {
          overlayDevi.style.opacity = "0";
          overlayDevi.style.transform = "scale(0.57)";
        }
        if (target === "Mike" && overlayMike) {
          overlayMike.style.opacity = "0";
          overlayMike.style.transform = "scale(0.61)";
        }
      }
    });

    // Clicking a character also triggers feedback toast
    zone.addEventListener("click", () => {
      const target = zone.getAttribute("data-target");
      showToast(tooltipMessages[target] || "Character selected!", "success");
    });
  });

  // Function to activate Smiling / Celebrating Audience Mode
  window.triggerAudienceSmileEffect = function (active = true) {
    isSmilingMode = active;
    if (active) {
      if (overlayJohn) {
        overlayJohn.style.opacity = "1";
        overlayJohn.style.transform = "scale(0.53)";
        overlayJohn.style.filter = "drop-shadow(0 0 18px rgba(46,70,55,0.45))";
      }
      if (overlayDevi) {
        overlayDevi.style.opacity = "1";
        overlayDevi.style.transform = "scale(0.60)";
        overlayDevi.style.filter = "drop-shadow(0 0 18px rgba(46,70,55,0.45))";
      }
      if (overlayMike) {
        overlayMike.style.opacity = "1";
        overlayMike.style.transform = "scale(0.64)";
        overlayMike.style.filter = "drop-shadow(0 0 18px rgba(46,70,55,0.45))";
      }
      if (stageMoodBadge) {
        stageMoodBadge.innerHTML = `<i class="bi bi-emoji-laughing-fill me-1"></i> 🌟 Audience Smiling & Engaged (Good Speech!)`;
        stageMoodBadge.style.backgroundColor = "#E8F5E9";
        stageMoodBadge.style.color = "#2E7D32";
        stageMoodBadge.style.borderColor = "#A5D6A7";
      }
      showToast("🎉 Excellent speaking flow! Your audience is smiling and celebrating your delivery!", "success");
    } else {
      if (overlayJohn) {
        overlayJohn.style.opacity = "0";
        overlayJohn.style.transform = "scale(0.50)";
        overlayJohn.style.filter = "none";
      }
      if (overlayDevi) {
        overlayDevi.style.opacity = "0";
        overlayDevi.style.transform = "scale(0.57)";
        overlayDevi.style.filter = "none";
      }
      if (overlayMike) {
        overlayMike.style.opacity = "0";
        overlayMike.style.transform = "scale(0.61)";
        overlayMike.style.filter = "none";
      }
      if (stageMoodBadge) {
        stageMoodBadge.innerHTML = `<i class="bi bi-emoji-neutral me-1"></i> Attentive Audience`;
        stageMoodBadge.style.backgroundColor = "#EBF1ED";
        stageMoodBadge.style.color = "#2E4637";
        stageMoodBadge.style.borderColor = "#D2DFD6";
      }
    }
  };
  if (btnToggleSmileEffect) {
    btnToggleSmileEffect.addEventListener("click", () => {
      window.triggerAudienceSmileEffect(!isSmilingMode);
    });
  }
  
  const btnEnableCamera = document.getElementById('btnEnableCamera');
  if (btnEnableCamera) {
    const initCamera = async () => {
      btnEnableCamera.disabled = true;
      btnEnableCamera.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Loading FaceMesh...';
      try {
        if (!window.WebcamAnalyzer) {
          throw new Error("WebcamAnalyzer not loaded");
        }
        webcamAnalyzer = new window.WebcamAnalyzer(
          document.getElementById('webcamPreview'),
          document.getElementById('webcamIndicator')
        );
        await webcamAnalyzer.initialize();
        btnEnableCamera.innerHTML = '<i class="bi bi-check-circle-fill text-success"></i> Camera Active';
      } catch (err) {
        console.error("Camera init failed:", err);
        btnEnableCamera.innerHTML = '<i class="bi bi-exclamation-triangle-fill text-danger"></i> Failed';
      }
    };
    btnEnableCamera.addEventListener('click', initCamera);
    // Auto-start camera on page load
    setTimeout(initCamera, 500);
  }
});


