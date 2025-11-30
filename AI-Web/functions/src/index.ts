/**
 * Import function triggers from their respective submodules:
 *
 * import {onCall} from "firebase-functions/v2/https";
 * import {onDocumentWritten} from "firebase-functions/v2/firestore";
 *
 * See a full list of supported triggers at https://firebase.google.com/docs/functions
 */

import { setGlobalOptions } from "firebase-functions";


const cors = require("cors");
// Start writing functions
// https://firebase.google.com/docs/functions/typescript

// For cost control, you can set the maximum number of containers that can be
// running at the same time. This helps mitigate the impact of unexpected
// traffic spikes by instead downgrading performance. This limit is a
// per-function limit. You can override the limit for each function using the
// `maxInstances` option in the function's options, e.g.
// `onRequest({ maxInstances: 5 }, (req, res) => { ... })`.
// NOTE: setGlobalOptions does not apply to functions using the v1 API. V1
// functions should each use functions.runWith({ maxInstances: 10 }) instead.
// In the v1 API, each function can only serve one request per container, so
// this will be the maximum concurrent request count.

import * as functions from "firebase-functions";
import * as admin from "firebase-admin";

setGlobalOptions({ maxInstances: 10 });

admin.initializeApp();



const corsHandler = cors({ origin: true });

export const sendResetPassword = functions.https.onRequest((req, res) => {
	corsHandler(req, res, () => {
		res.setHeader('Access-Control-Allow-Origin', '*');
		res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
		res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
		if (req.method === 'OPTIONS') {
			// Trả về cho preflight request
			return res.status(204).send('');
		}
		if (req.method !== "POST") {
			return res.status(405).send("Method Not Allowed");
		}
		// Không làm gì, chỉ trả về thành công
		return res.status(200).send({ success: true });
	});
});

/**
 * Gửi email nhắc nhở uống thuốc
 */
export const sendMedicineReminder = functions.https.onRequest((req, res) => {
	corsHandler(req, res, async () => {
		res.setHeader('Access-Control-Allow-Origin', '*');
		res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
		res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
		
		if (req.method === 'OPTIONS') {
			return res.status(204).send('');
		}
		
		if (req.method !== "POST") {
			return res.status(405).send("Method Not Allowed");
		}

		try {
			const { email, medicine_name, time, message } = req.body;

			if (!email || !medicine_name) {
				return res.status(400).send({ error: "Email và tên thuốc là bắt buộc" });
			}

			// TODO: Gửi email thực tế qua nodemailer hoặc SendGrid
			// Tạm thời chỉ log
			console.log(`📧 Gửi email nhắc nhở đến ${email}:`);
			console.log(`   Thuốc: ${medicine_name}`);
			console.log(`   Giờ: ${time}`);
			console.log(`   Nội dung: ${message}`);

			// Nếu có cấu hình email, gửi thật
			// const transporter = nodemailer.createTransport({...});
			// await transporter.sendMail({...});

			return res.status(200).send({ 
				success: true, 
				message: "Đã gửi thông báo nhắc nhở" 
			});
		} catch (error: any) {
			console.error("Lỗi khi gửi email nhắc nhở:", error);
			return res.status(500).send({ error: error.message });
		}
	});
});

// export const helloWorld = onRequest((request, response) => {
//   logger.info("Hello logs!", {structuredData: true});
//   response.send("Hello from Firebase!");
// });
