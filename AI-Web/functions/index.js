const functions = require('firebase-functions');
const admin = require('firebase-admin');
const nodemailer = require('nodemailer');
const cors = require('cors')({ origin: true });
admin.initializeApp();

const gmailEmail = 'YOUR_ADMIN_EMAIL@gmail.com';
const gmailPassword = 'YOUR_APP_PASSWORD'; // dùng App Password nếu bật 2FA

const transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: gmailEmail,
    pass: gmailPassword,
  },
});

exports.sendResetPassword = functions.https.onRequest((req, res) => {
  cors(req, res, async () => {
    if (req.method !== 'POST') {
      return res.status(405).send('Method Not Allowed');
    }
    const { email, username } = req.body;
    const newPassword = Math.random().toString(36).slice(-8);
    const passwordHash = Buffer.from(newPassword).toString('base64');

    try {
      const userRef = admin.firestore().collection('userCredentials').where('email', '==', email);
      const snapshot = await userRef.get();
      if (snapshot.empty) return res.status(404).send({ error: 'Email không tồn tại' });

      await snapshot.docs[0].ref.update({
        passwordHash,
        forceChangePassword: true,
        updatedAt: admin.firestore.FieldValue.serverTimestamp(),
      });

      const mailOptions = {
        from: gmailEmail,
        to: email,
        subject: 'Mật khẩu mới cho tài khoản của bạn',
        text: `Mật khẩu mới của bạn là: ${newPassword}\nVui lòng đăng nhập và đổi mật khẩu ngay lập tức.`,
      };

      await transporter.sendMail(mailOptions);
      return res.status(200).send({ success: true });
    } catch (err) {
      return res.status(500).send({ error: err.message });
    }
  });
});
